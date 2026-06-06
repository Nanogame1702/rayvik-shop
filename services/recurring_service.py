"""
Сервис для работы с повторяющимися рассылками
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import logging
from typing import Optional

from database import (
    get_recurring_broadcast,
    update_recurring_broadcast_stats,
    log_recurring_send,
    list_recurring_broadcasts
)

logger = logging.getLogger(__name__)


class RecurringBroadcastService:
    """Сервис для работы с повторяющимися рассылками"""
    
    @staticmethod
    def calculate_next_send_time(
        pattern: str,
        schedule_time: str,
        schedule_days: Optional[str] = None,
        day_of_month: Optional[int] = None,
        timezone: str = "Europe/Moscow",
        from_time: Optional[datetime] = None
    ) -> datetime:
        """
        Расчет следующего времени отправки
        
        Args:
            pattern: 'daily', 'weekly', 'monthly'
            schedule_time: 'HH:MM'
            schedule_days: JSON массив дней недели для weekly [1,2,3]
            day_of_month: День месяца для monthly
            timezone: Часовой пояс
            from_time: От какого времени считать (по умолчанию - сейчас)
        
        Returns:
            datetime: Следующее время отправки в UTC
        """
        tz = ZoneInfo(timezone)
        current = from_time or datetime.now(tz)
        
        # Парсим время
        try:
            hour, minute = map(int, schedule_time.split(':'))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid schedule_time format: {schedule_time}")
        
        if pattern == 'daily':
            # Ежедневно
            next_time = current.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            
            # Если время уже прошло сегодня, берем завтра
            if next_time <= current:
                next_time += timedelta(days=1)
        
        elif pattern == 'weekly':
            # Еженедельно
            if not schedule_days:
                raise ValueError("schedule_days required for weekly pattern")
            
            try:
                days = json.loads(schedule_days)  # [1, 3, 5] - пн, ср, пт
            except (json.JSONDecodeError, TypeError):
                raise ValueError(f"Invalid schedule_days format: {schedule_days}")
            
            if not days:
                raise ValueError("schedule_days cannot be empty for weekly pattern")
            
            current_weekday = current.isoweekday()  # 1-7
            
            # Ищем ближайший день
            next_time = None
            for day in sorted(days):
                days_ahead = day - current_weekday
                if days_ahead < 0:
                    days_ahead += 7
                
                candidate = current + timedelta(days=days_ahead)
                candidate = candidate.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
                
                if candidate > current:
                    next_time = candidate
                    break
            
            # Если не нашли на этой неделе, берем первый день следующей
            if not next_time:
                days_ahead = (days[0] - current_weekday) % 7 + 7
                next_time = current + timedelta(days=days_ahead)
                next_time = next_time.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
        
        elif pattern == 'monthly':
            # Ежемесячно
            if not day_of_month:
                raise ValueError("day_of_month required for monthly pattern")
            
            if not (1 <= day_of_month <= 31):
                raise ValueError(f"day_of_month must be between 1 and 31, got {day_of_month}")
            
            # Пробуем текущий месяц
            try:
                next_time = current.replace(
                    day=day_of_month,
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
            except ValueError:
                # День не существует в этом месяце (например, 31 февраля)
                # Берем последний день месяца
                next_month = current.replace(day=1) + timedelta(days=32)
                next_time = next_month.replace(day=1) - timedelta(days=1)
                next_time = next_time.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )
            
            # Если время уже прошло, берем следующий месяц
            if next_time <= current:
                if current.month == 12:
                    next_time = next_time.replace(year=current.year + 1, month=1)
                else:
                    next_time = next_time.replace(month=current.month + 1)
                
                # Снова проверяем существование дня
                try:
                    next_time = next_time.replace(day=day_of_month)
                except ValueError:
                    # Берем последний день месяца
                    next_month = next_time.replace(day=1) + timedelta(days=32)
                    next_time = next_month.replace(day=1) - timedelta(days=1)
        
        else:
            raise ValueError(f"Unknown pattern: {pattern}")
        
        # Конвертируем в UTC
        return next_time.astimezone(ZoneInfo("UTC"))
    
    
    @staticmethod
    async def create_scheduled_task_from_recurring(recurring_id: int) -> Optional[int]:
        """
        Создание задачи в scheduled_broadcasts из recurring broadcast
        
        Returns:
            int: ID созданной задачи или None при ошибке
        """
        try:
            from services import scheduled_repo
        except ImportError:
            logger.error("scheduled_repo not found, cannot create scheduled task")
            return None
        
        recurring = await get_recurring_broadcast(recurring_id)
        if not recurring:
            logger.warning(f"Recurring broadcast {recurring_id} not found")
            return None
        
        if not recurring['is_active']:
            logger.info(f"Recurring broadcast {recurring_id} is not active, skipping")
            return None
        
        try:
            # Рассчитываем следующее время
            next_time = RecurringBroadcastService.calculate_next_send_time(
                pattern=recurring['schedule_pattern'],
                schedule_time=recurring['schedule_time'],
                schedule_days=recurring['schedule_days'] if 'schedule_days' in recurring.keys() else None,
                day_of_month=recurring['schedule_day_of_month'] if 'schedule_day_of_month' in recurring.keys() else None,
                timezone=recurring['timezone']
            )
            
            # Создаем задачу
            await scheduled_repo.ensure_schema()
            
            # Добавляем recurring_id в keyboard_json для связи
            keyboard_data = json.loads(recurring['keyboard_json'] or '[]')
            if isinstance(keyboard_data, dict):
                keyboard_data['_recurring_id'] = recurring_id
            else:
                keyboard_data = {'buttons': keyboard_data, '_recurring_id': recurring_id}
            
            task_id = await scheduled_repo.create(
                audience=recurring['audience'],
                text=recurring['text'],
                parse_mode=recurring['parse_mode'],
                keyboard_json=json.dumps(keyboard_data, ensure_ascii=False),
                scheduled_at_utc=next_time.isoformat(),
                tz=recurring['timezone'],
                created_by=recurring['created_by']
            )
            
            # Обновляем next_send_at
            await update_recurring_broadcast_stats(
                recurring_id=recurring_id,
                next_send_at=next_time.isoformat(),
                increment_sends=False
            )
            
            logger.info(f"Created scheduled task {task_id} for recurring broadcast {recurring_id}")
            return task_id
            
        except Exception as e:
            logger.exception(f"Error creating scheduled task for recurring {recurring_id}: {e}")
            return None
    
    
    @staticmethod
    async def process_completed_broadcast(scheduled_task, success: bool, error: str = None, recipients_count: int = 0):
        """
        Обработка завершенной рассылки
        
        Args:
            scheduled_task: Задача из scheduled_broadcasts (dict или Row)
            success: Успешно ли выполнена
            error: Сообщение об ошибке (если есть)
            recipients_count: Количество получателей
        """
        try:
            # Проверяем, связана ли с recurring
            keyboard_json = scheduled_task['keyboard_json'] if 'keyboard_json' in scheduled_task.keys() else '[]'
            try:
                keyboard_data = json.loads(keyboard_json)
                recurring_id = None
                
                if isinstance(keyboard_data, dict):
                    recurring_id = keyboard_data.get('_recurring_id')
                
                if not recurring_id:
                    logger.debug("Task is not linked to recurring broadcast")
                    return  # Это обычная одноразовая рассылка
                
            except (json.JSONDecodeError, TypeError):
                logger.debug("Could not parse keyboard_json")
                return
            
            # Логируем отправку
            await log_recurring_send(
                recurring_id=recurring_id,
                status='success' if success else 'failed',
                error_message=error,
                recipients_count=recipients_count
            )
            
            # Обновляем статистику
            now = datetime.now(ZoneInfo("UTC"))
            await update_recurring_broadcast_stats(
                recurring_id=recurring_id,
                last_sent_at=now.isoformat(),
                increment_sends=success  # Увеличиваем счетчик только при успехе
            )
            
            # Создаем следующую задачу (даже если была ошибка)
            next_task_id = await RecurringBroadcastService.create_scheduled_task_from_recurring(recurring_id)
            
            if next_task_id:
                logger.info(f"Created next task {next_task_id} for recurring {recurring_id}")
            else:
                logger.warning(f"Failed to create next task for recurring {recurring_id}")
                
        except Exception as e:
            logger.exception(f"Error processing completed broadcast: {e}")
    
    
    @staticmethod
    async def sync_recurring_schedules(bot):
        """
        Синхронизация расписаний при старте бота
        Проверяет все активные recurring broadcasts и создает задачи если нужно
        """
        try:
            from services import scheduled_repo
        except ImportError:
            logger.error("scheduled_repo not found, cannot sync schedules")
            return
        
        try:
            active_broadcasts = await list_recurring_broadcasts(active_only=True)
            logger.info(f"Syncing {len(active_broadcasts)} active recurring broadcasts")
            
            for broadcast in active_broadcasts:
                recurring_id = broadcast['id']
                
                try:
                    # Проверяем, есть ли уже запланированная задача
                    # Ищем задачи с recurring_id в keyboard_json
                    all_pending = await scheduled_repo.list_upcoming(limit=1000)
                    
                    has_pending = False
                    for task in all_pending:
                        try:
                            task_keyboard = task['keyboard_json'] if 'keyboard_json' in task.keys() else '[]'
                            keyboard_data = json.loads(task_keyboard)
                            if isinstance(keyboard_data, dict):
                                if keyboard_data.get('_recurring_id') == recurring_id:
                                    has_pending = True
                                    break
                        except:
                            continue
                    
                    if not has_pending:
                        # Нет задачи - создаем
                        task_id = await RecurringBroadcastService.create_scheduled_task_from_recurring(recurring_id)
                        if task_id:
                            logger.info(f"Created missing task {task_id} for recurring {recurring_id}")
                    else:
                        logger.debug(f"Recurring {recurring_id} already has pending task")
                        
                except Exception as e:
                    logger.exception(f"Error syncing recurring {recurring_id}: {e}")
                    continue
            
            logger.info("Recurring schedules sync completed")
            
        except Exception as e:
            logger.exception(f"Error syncing recurring schedules: {e}")
