import json
import os

# Default categories if file doesn't exist or is corrupted
DEFAULT_CATEGORIES = [
    "Technology",
    "Politics",
    "Entertainment",
    "Sports",
    "Science",
    "Business",
    "World News"
]

# Path to categories JSON file
CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'categories.json')


def load_categories():
    """
    Load categories from JSON file.

    Returns:
        list: List of category names
    """
    try:
        if os.path.exists(CATEGORIES_FILE):
            with open(CATEGORIES_FILE, 'r') as f:
                data = json.load(f)
                categories = data.get('categories', DEFAULT_CATEGORIES)
                # Ensure we have at least some categories
                if not categories or len(categories) == 0:
                    return DEFAULT_CATEGORIES.copy()
                return categories
        else:
            # File doesn't exist, create it with defaults
            save_categories(DEFAULT_CATEGORIES)
            return DEFAULT_CATEGORIES.copy()
    except Exception as e:
        print(f"Warning: Could not load categories from {CATEGORIES_FILE}: {e}")
        print("Using default categories")
        return DEFAULT_CATEGORIES.copy()


def save_categories(categories):
    """
    Save categories to JSON file.

    Args:
        categories: List of category names
    """
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(CATEGORIES_FILE), exist_ok=True)

        data = {"categories": categories}
        with open(CATEGORIES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error: Could not save categories to {CATEGORIES_FILE}: {e}")
        return False


def add_category(name):
    """
    Add a new category.

    Args:
        name: Category name to add

    Returns:
        tuple: (success: bool, message: str)
    """
    if not name or not name.strip():
        return False, "Category name cannot be empty"

    name = name.strip()
    categories = load_categories()

    # Check if category already exists (case-insensitive)
    if any(cat.lower() == name.lower() for cat in categories):
        return False, f"Category '{name}' already exists"

    categories.append(name)
    if save_categories(categories):
        return True, f"Added category '{name}'"
    else:
        return False, "Failed to save categories"


def remove_category(name):
    """
    Remove a category.

    Args:
        name: Category name to remove

    Returns:
        tuple: (success: bool, message: str)
    """
    if not name or not name.strip():
        return False, "Category name cannot be empty"

    name = name.strip()
    categories = load_categories()

    # Find category (case-insensitive)
    found = None
    for cat in categories:
        if cat.lower() == name.lower():
            found = cat
            break

    if not found:
        return False, f"Category '{name}' not found"

    # Require at least 2 categories
    if len(categories) <= 2:
        return False, "Cannot remove category - at least 2 categories are required"

    categories.remove(found)
    if save_categories(categories):
        return True, f"Removed category '{found}'"
    else:
        return False, "Failed to save categories"


def list_categories():
    """
    Get current list of categories.

    Returns:
        list: List of category names
    """
    return load_categories()


def reset_to_defaults():
    """
    Reset categories to default list.

    Returns:
        bool: Success status
    """
    return save_categories(DEFAULT_CATEGORIES.copy())
