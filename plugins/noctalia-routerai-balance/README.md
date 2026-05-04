# RouterAI Balance

Плагин для Noctalia, отображающий баланс аккаунта RouterAI.

## Установка

1. Скопируйте плагин в директорию плагинов Noctalia:
   ```bash
   cp -r plugins/noctalia-routerai-balance ~/.config/noctalia/plugins/routerai-balance
   ```

2. Зарегистрируйте плагин в `~/.config/noctalia/plugins.json`:
   ```json
   {
     "routerai-balance": {
       "enabled": true
     }
   }
   ```

3. Перезапустите Noctalia или включите плагин через настройки.

## Использование

### Bar Widget

Добавьте виджет в bar через настройки Noctalia (Settings > Bar).

### Desktop Widget

Добавьте виджет на рабочий стол через настройки Noctalia (Settings > Desktop Widgets).

### Настройка API ключа

1. Создайте API ключ на [routerai.ru](https://routerai.ru/settings/keys)
2. На Desktop Widget нажмите кнопку настроек (шестерёнка)
3. Введите ваш API ключ
4. Настройте интервал обновления (в секундах)
5. Нажмите "Save"

## Требования

- Noctalia версии 3.6.0 или выше

## Лицензия

MIT