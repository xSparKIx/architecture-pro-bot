# Задание 6

## Описание
Сервис автоматически обновляет базу знаний раз в `CHECK_INTERVAL` (по станадрту каждые 24 часа).

## Что происходит при каждом запуске:
1. Загружается состояние из `update_state.json`
2. Для каждого файла вычисляется текущий MD5 хеш
3. Сравнивается с сохраненным хешем
4. Если хеши разные → файл изменился → добавляем в список обновлений
5. Сохраняем новые хеши в состояние
6. Удаляем из состояния файлы, которых больше нет в папке
7. Сохраняем файл `update_summary.json` с списком измененных данных

## Пример состояния:
```json
{
  "last_update": "2026-01-25T19:13:34.545702",
  "file_hashes": {
    "/home/sparki/projects/architecture-pro-bot/task6/../task2/knowledge_base/place_Hoth.md": "871064ea51d9540fb59bcce34d89e004"
  },
  "total_files": 1,
  "total_chunks": 3
}
```

## Пример файла с изменениями:
```json
{
  "timestamp": "2026-01-25T19:12:07.732618",
  "files_processed": 1,
  "chunks_created": 3,
  "duration_seconds": 0.06,
  "tracked_files_count": 1,
  "file_list": [
    {
      "path": "/home/sparki/projects/architecture-pro-bot/task6/../task2/knowledge_base/place_Hoth.md",
      "status": "new",
      "hash": "871064ea51d9540fb59bcce34d89e004",
      "old_hash": null
    }
  ]
}
```