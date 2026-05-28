# Backlog

Дата актуализации: 2026-05-26.

Этот файл фиксирует только P0 backlog. Остальные блоки данных переводятся в реализацию.

## P0. Потери

Цель: закрыть журнал операций iikoServer для контроля удалений, списаний, возвратов, отмен и ручных скидок. Это не "причины потерь" в абстрактном смысле, а конкретные операции в системе.

Нужно получить:

- writeoffs;
- deletions;
- refunds;
- cancellations;
- manual discounts;
- основание/комментарий операции, если iikoServer его отдает;
- user/employee/cashier/operator операции, если доступно.

План:

1. Найти в iikoServer-доке источник operation journal/audit для операций по заказам.
2. Сохранить полный catalog OLAP columns для `SALES`, `TRANSACTIONS`, `DELIVERIES`.
3. Вручную разобрать поля writeoff/deletion/refund/cancel/comment/user/employee.
4. Не угадывать ручки и имена полей: брать только то, что есть в iikoServer документации, operation journal/audit API и `/v2/reports/olap/columns`.
5. Добавить raw/upsert слой для найденного operation journal/OLAP source.
6. Расширить `fact_losses` типами `writeoff`, `deletion`, `manual_discount`, `refund`, `cancellation`, `late_delivery`.
7. Привязать сотрудника/пользователя операции, если поле реально есть в iikoServer.
8. Пересобрать `mart_losses` из единой taxonomy.
