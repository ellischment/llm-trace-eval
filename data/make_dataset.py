"""Regenerates data/eval50.jsonl: 25 capital-city questions + 25 arithmetic questions."""
import json
from pathlib import Path

CAPITALS = [("France", "Paris"), ("Germany", "Berlin"), ("Italy", "Rome"), ("Spain", "Madrid"),
            ("Portugal", "Lisbon"), ("Poland", "Warsaw"), ("Norway", "Oslo"), ("Sweden", "Stockholm"),
            ("Finland", "Helsinki"), ("Greece", "Athens"), ("Austria", "Vienna"), ("Hungary", "Budapest"),
            ("Japan", "Tokyo"), ("Egypt", "Cairo"), ("Kenya", "Nairobi"), ("Peru", "Lima"),
            ("Chile", "Santiago"), ("Canada", "Ottawa"), ("Australia", "Canberra"), ("Turkey", "Ankara"),
            ("Ukraine", "Kyiv"), ("Ireland", "Dublin"), ("Thailand", "Bangkok"), ("Argentina", "Buenos Aires"),
            ("Morocco", "Rabat")]
ARITH = [(7, 8, "*"), (12, 13, "*"), (9, 9, "*"), (15, 4, "*"), (25, 6, "*"), (11, 11, "*"),
         (123, 456, "+"), (999, 1, "+"), (250, 750, "+"), (87, 34, "+"), (1000, 1, "-"), (500, 123, "-"),
         (64, 8, "/"), (144, 12, "/"), (81, 9, "/"), (17, 5, "+"), (300, 45, "-"), (14, 14, "*"),
         (36, 6, "/"), (45, 55, "+"), (200, 88, "-"), (13, 7, "*"), (72, 9, "/"), (19, 21, "+"), (90, 17, "-")]
OPS = {"+": lambda a, b: a + b, "-": lambda a, b: a - b, "*": lambda a, b: a * b, "/": lambda a, b: a // b}

rows = [{"question": f"What is the capital of {c}? Answer with the city name only.", "answer": a} for c, a in CAPITALS]
rows += [{"question": f"Compute {a} {op} {b}. Answer with the number only.", "answer": str(OPS[op](a, b))}
         for a, b, op in ARITH]
assert len(rows) == 50
out = Path(__file__).with_name("eval50.jsonl")
out.write_text("\n".join(json.dumps({"id": i, **r}) for i, r in enumerate(rows)) + "\n", encoding="utf-8")
