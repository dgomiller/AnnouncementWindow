
import Config
import Filters

print("Initial window_count:", Filters.expressions.window_count)
initial_keys = list(list(Filters.expressions.groups.values())[0].categories.values())[0].show.keys()
print("Initial keys:", initial_keys)

# Simulate Window.py initialization
# Config.settings.window_count is 5
for i in range(Config.settings.window_count):
    print(f"Calling add_window({i})")
    Filters.expressions.add_window(i)

print("Post-Window-init window_count:", Filters.expressions.window_count)

# Simulate TagConfig opening which calls reload()
print("Reloading Filters...")
Filters.expressions.reload()

print("Final window_count:", Filters.expressions.window_count)
final_keys = list(list(Filters.expressions.groups.values())[0].categories.values())[0].show.keys()
print("Final keys:", final_keys)
print("Count of keys:", len(final_keys))

if len(final_keys) > Config.settings.window_count:
    print("BUG REPRODUCED: More keys than configured.")
else:
    print("Bug not reproduced.")
