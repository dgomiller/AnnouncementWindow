
import sys
import os

# Create logic to verify the window counts and data structures
import Config
import Filters

print("Config.settings.window_count:", Config.settings.window_count)
print("Filters.expressions.window_count:", Filters.expressions.window_count)

# Check the first category's show keys
try:
    first_group = list(Filters.expressions.groups.values())[0]
    first_cat = list(first_group.categories.values())[0]
    print("First category:", first_cat.category)
    print("First category show keys:", first_cat.show.keys())
    
    # Check if there are any categories with extra keys
    for g_name, group in Filters.expressions.groups.items():
        for c_name, cat in group.categories.items():
            if len(cat.show.keys()) > Config.settings.window_count:
                print(f"FAIL: Category '{c_name}' in group '{g_name}' has keys: {cat.show.keys()}")
                break
except Exception as e:
    print("Error checking categories:", e)
