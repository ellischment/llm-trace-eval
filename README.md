# llm-trace-eval

Маленький каркас, который я собрала, чтобы смотреть на eval LLM через трассы, а не через один финальный процент. Каждый вызов модели живёт внутри спана OpenTelemetry `llm.call` с моделью, промптом, ответом, задержкой и токенами. Прогон датасета даёт один родительский спан `eval.run` и по дочернему `eval.example` на каждый пример, так что в любом коллекторе видно, какой пример сколько ждал, что вернула модель и почему ответ не засчитали. Всё это без внешних сервисов: по умолчанию трассы пишутся в `traces.jsonl`, одна строка на спан, и их можно читать хоть `jq`, хоть pandas.

Датасет на 50 вопросов (25 столиц, 25 арифметических) я сгенерировала скриптом `data/make_dataset.py`. Это не бенчмарк, а проверка конвейера: ответы известны, модель отвечает одним словом или числом, метрика честная. Под свои данные достаточно подложить другой `.jsonl` с полями `id`, `question`, `answer`.

Accuracy считается как точное совпадение после нормализации: регистр, кавычки, точка в конце и пробелы не мешают, а вот «Not Paris, Milan» за «Paris» не засчитывается, и «-5» не равно «5». Такой выбор сознательный: при промпте «ответь только городом» любое вхождение подстроки раздувает метрику, а понять, где именно модель ошиблась, потом невозможно.

## Запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
pytest
```

Без ключа работает бэкенд `mock`: он всегда отвечает «42». В датасете ровно один пример с таким ответом (`Compute 6 * 7`), поэтому mock даёт accuracy 2.00%: видно и что конвейер с трассами собирается от начала до конца, и что метрика отличает верный ответ от неверного. Реальная модель:

```bash
export ANTHROPIC_API_KEY=...
python run.py --backend anthropic --model claude-haiku-5-5
```

Полезные флаги: `--limit N` прогоняет первые N примеров, `--dataset` и `--out` меняют вход и выход. Результат пишется в `results.json` (сводка плюс строка на пример с полями `id`, `question`, `gold`, `response`, `correct`), трассы в `traces.jsonl` (путь можно сменить через `TRACE_FILE`). Если задан `OTEL_EXPORTER_OTLP_ENDPOINT`, спаны уходят в OTLP-коллектор по HTTP вместо файла.

Так выглядит один спан `llm.call` в `traces.jsonl` (сокращённо):

```json
{"name": "llm.call", "context": {"trace_id": "0x52d3…", "span_id": "0x95ac…"}, "parent_id": "0xd72e…",
 "start_time": "2026-10-28T11:14:34.916106Z", "end_time": "2026-10-28T11:14:34.916157Z",
 "status": {"status_code": "UNSET"},
 "attributes": {"llm.backend": "mock", "llm.model": "claude-haiku-5-5",
                "llm.prompt": "What is the capital of France? Answer with the city name only.",
                "llm.latency_s": 8.08e-06, "llm.response": "42",
                "llm.usage.input_tokens": 12, "llm.usage.output_tokens": 1},
 "resource": {"attributes": {"service.name": "llm-trace-eval"}}}
```

Упавший вызов не роняет прогон: исключение записывается в спан со статусом `ERROR`, а пример засчитывается как неверный с `response` вида `ERROR: …`.

## Структура

```
run.py                      точка входа: аргументы, трассировка, запись results.json
llm_trace_eval/
  client.py                 call_llm(): один вызов модели внутри спана llm.call; бэкенды mock и anthropic
  harness.py                run_eval(): спаны eval.run / eval.example, is_correct(), чтение датасета
  tracing.py                настройка OpenTelemetry: JSONL-файл или OTLP, flush и shutdown
data/
  eval50.jsonl              50 примеров
  make_dataset.py           генератор датасета
tests/
  test_harness.py           is_correct, прогон в mock-режиме, дерево спанов, отсутствующий датасет
requirements.txt            закреплённые версии
```

## Ограничения

- Метрика только точное совпадение после нормализации; нет оценки неопределённости и детекции ошибок.
- Датасет синтетический и лёгкий.
- Один вызов на пример, без повторов и ретраев.

## Лицензия

MIT, см. `LICENSE`.
