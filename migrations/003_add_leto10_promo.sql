-- Добавление промокода ЛЕТО10 (50% скидка, 11 использований)
INSERT OR IGNORE INTO promocodes (code, discount, description, max_uses, current_uses, is_active)
VALUES ('ЛЕТО10', 50, 'Летняя акция 50% скидка', 11, 0, 1);
