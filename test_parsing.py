from parsing import extract_json_object, normalize_and_validate_action

raw = """
Sure! Here is the JSON:
{
  "reasoning": "P2 was inconsistent.",
  "action": "VOTE",
  "target": "P2",
  "utterance": ""
}
Thanks!
"""

obj = extract_json_object(raw)
print("obj:", obj)
print("normalized:", normalize_and_validate_action(obj, phase="VOTE"))