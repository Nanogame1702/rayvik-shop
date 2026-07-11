-- Добавление промокода START10 (10% скидка, 10 использований)
INSERT OR IGNORE INTO promocodes (code, discount, description, max_uses, current_uses, is_active)
VALUES ('START10', 10, 'Стартовая скидка 10%', 10, 0, 1);
