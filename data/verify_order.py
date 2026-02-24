#!/usr/bin/env python3
"""Quick verify that reasoning comes before answer in aagent output."""
import json

# Check alpaca
with open('/Users/aayushtyagi/Aayush/PhD/Learning/Hackathron/AMD_Hackathron/AAIPL/data/final/aagent_alpaca_train.json') as f:
    data = json.load(f)
print('=== Alpaca Train ===')
print(f'Instruction: {data[0]["instruction"]}')
print(f'Output 1: {data[0]["output"][:300]}')
print(f'Output 2: {data[1]["output"][:300]}')
print()

# Check chatml
with open('/Users/aayushtyagi/Aayush/PhD/Learning/Hackathron/AMD_Hackathron/AAIPL/data/final/aagent_chatml_train.json') as f:
    data = json.load(f)
print('=== ChatML Train ===')
print(f'System: {data[0]["messages"][0]["content"]}')
print(f'Assistant: {data[0]["messages"][-1]["content"][:300]}')
print()

# Verify key order in both formats
out_chatml = json.loads(data[0]['messages'][-1]['content'])
keys_chatml = list(out_chatml.keys())
print(f'ChatML JSON key order: {keys_chatml}')

with open('/Users/aayushtyagi/Aayush/PhD/Learning/Hackathron/AMD_Hackathron/AAIPL/data/final/aagent_alpaca_train.json') as f:
    adata = json.load(f)
out_alpaca = json.loads(adata[0]['output'])
keys_alpaca = list(out_alpaca.keys())
print(f'Alpaca JSON key order: {keys_alpaca}')

assert keys_chatml[0] == 'reasoning', f'FAIL: first key should be reasoning, got {keys_chatml[0]}'
assert keys_chatml[1] == 'answer', f'FAIL: second key should be answer, got {keys_chatml[1]}'
assert keys_alpaca[0] == 'reasoning', f'FAIL: first key should be reasoning, got {keys_alpaca[0]}'
assert keys_alpaca[1] == 'answer', f'FAIL: second key should be answer, got {keys_alpaca[1]}'
print('\nAll good - reasoning comes first, answer second')
