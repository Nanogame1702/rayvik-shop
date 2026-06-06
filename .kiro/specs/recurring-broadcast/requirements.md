# Requirements Document

## Introduction

Система автоматической повторяющейся рассылки для Telegram-бота магазина Luno Shop. Позволяет администратору настроить рассылку, которая будет автоматически отправляться каждый день в заданное время (например, каждое утро в 9:00).

## Glossary

- **Recurring Broadcast (Повторяющаяся рассылка)**: Автоматическая рассылка, которая отправляется по расписанию (ежедневно, еженедельно и т.д.)
- **Broadcast System (Система рассылок)**: Существующая система отложенных рассылок в боте
- **Admin (Администратор)**: Пользователь с правами управления ботом (ADMIN_ID)
- **Audience (Аудитория)**: Целевая группа получателей (все пользователи или только покупатели)
- **Schedule Pattern (Паттерн расписания)**: Правило повторения (daily, weekly, monthly)
- **Active Status (Активный статус)**: Состояние рассылки (включена/выключена)

## Requirements

### Requirement 1

**User Story:** As an administrator, I want to create a recurring daily broadcast, so that I can automatically send promotional messages every morning without manual intervention.

#### Acceptance Criteria

1. WHEN an administrator creates a recurring broadcast THEN the system SHALL store the broadcast template with schedule pattern
2. WHEN the scheduled time arrives THEN the system SHALL automatically send the broadcast to the specified audience
3. WHEN a broadcast is sent THEN the system SHALL schedule the next occurrence based on the pattern
4. WHEN an administrator views recurring broadcasts THEN the system SHALL display all active and inactive recurring broadcasts with their next send time
5. WHEN an administrator deactivates a recurring broadcast THEN the system SHALL stop scheduling future occurrences

### Requirement 2

**User Story:** As an administrator, I want to configure the time and frequency of recurring broadcasts, so that I can control when and how often messages are sent.

#### Acceptance Criteria

1. WHEN creating a recurring broadcast THEN the system SHALL allow selecting time in HH:MM format
2. WHEN creating a recurring broadcast THEN the system SHALL allow selecting frequency (daily, weekly, monthly)
3. WHEN selecting weekly frequency THEN the system SHALL allow choosing specific days of the week
4. WHEN selecting monthly frequency THEN the system SHALL allow choosing specific day of the month
5. WHEN time is specified THEN the system SHALL interpret it in Moscow timezone (Europe/Moscow)

### Requirement 3

**User Story:** As an administrator, I want to use the same message builder for recurring broadcasts as for one-time broadcasts, so that I have consistent functionality.

#### Acceptance Criteria

1. WHEN creating a recurring broadcast THEN the system SHALL provide the same text editor as one-time broadcasts
2. WHEN adding buttons to recurring broadcast THEN the system SHALL support up to 8 URL buttons
3. WHEN adding media to recurring broadcast THEN the system SHALL support photo attachments
4. WHEN previewing recurring broadcast THEN the system SHALL show exactly how the message will look
5. WHEN HTML formatting is used THEN the system SHALL preserve formatting in all sends

### Requirement 4

**User Story:** As an administrator, I want to manage existing recurring broadcasts, so that I can update, pause, or delete them as needed.

#### Acceptance Criteria

1. WHEN viewing recurring broadcasts list THEN the system SHALL display broadcast ID, name, schedule, status, and next send time
2. WHEN pausing a recurring broadcast THEN the system SHALL stop scheduling without deleting the template
3. WHEN resuming a recurring broadcast THEN the system SHALL recalculate next send time and continue scheduling
4. WHEN editing a recurring broadcast THEN the system SHALL update the template for future sends only
5. WHEN deleting a recurring broadcast THEN the system SHALL remove it permanently and cancel pending sends

### Requirement 5

**User Story:** As an administrator, I want to see statistics for recurring broadcasts, so that I can measure their effectiveness.

#### Acceptance Criteria

1. WHEN viewing a recurring broadcast THEN the system SHALL display total number of sends
2. WHEN viewing a recurring broadcast THEN the system SHALL display last send timestamp
3. WHEN viewing a recurring broadcast THEN the system SHALL display next scheduled send time
4. WHEN a send fails THEN the system SHALL log the error and continue with the schedule
5. WHEN viewing send history THEN the system SHALL show success/failure status for each occurrence

### Requirement 6

**User Story:** As an administrator, I want to test a recurring broadcast before activating it, so that I can verify the message looks correct.

#### Acceptance Criteria

1. WHEN creating a recurring broadcast THEN the system SHALL provide a "Send Test" option
2. WHEN sending a test THEN the system SHALL send the message only to the administrator
3. WHEN sending a test THEN the system SHALL not affect the recurring schedule
4. WHEN test is successful THEN the system SHALL allow activating the recurring broadcast
5. WHEN test fails THEN the system SHALL display the error message to the administrator

### Requirement 7

**User Story:** As a system, I want to handle timezone changes and daylight saving time correctly, so that broadcasts are sent at the intended local time.

#### Acceptance Criteria

1. WHEN daylight saving time changes THEN the system SHALL adjust send times to maintain local time consistency
2. WHEN storing schedule time THEN the system SHALL store both UTC and timezone information
3. WHEN calculating next send time THEN the system SHALL use timezone-aware datetime calculations
4. WHEN displaying times to administrator THEN the system SHALL show times in Moscow timezone
5. WHEN system restarts THEN the system SHALL recalculate all pending recurring broadcasts

### Requirement 8

**User Story:** As an administrator, I want to receive notifications about recurring broadcast execution, so that I can monitor the system.

#### Acceptance Criteria

1. WHEN a recurring broadcast is sent successfully THEN the system SHALL send a confirmation to the administrator
2. WHEN a recurring broadcast fails THEN the system SHALL send an error notification to the administrator
3. WHEN a recurring broadcast is about to expire (last occurrence) THEN the system SHALL notify the administrator
4. WHEN notification preferences are set THEN the system SHALL respect administrator's notification settings
5. WHEN multiple broadcasts are scheduled THEN the system SHALL batch notifications to avoid spam
