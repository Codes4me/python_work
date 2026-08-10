user_0 = {
    'username': 'efermi',
    'first': 'enrico',
    'last': 'fermi',
    'firsts': 'enrico',
    'affragado': "enrico",
}
user_0.setdefault("info",()).append("none")
seen_values = set()

for key, value in user_0.items():
    # Only execute when the value is completely new
    if value not in seen_values:
        seen_values.add(value)

        print(f"Key: {key}")
        print(f"Value: {value}")