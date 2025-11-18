"""
Manage Filler Words Database
Script to add, remove, or view filler words in the SQLite database.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from basic_agent import FillerWord, Base

# Database setup
engine = create_engine('sqlite:///filler_words.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def view_all_words():
    """Display all filler words in the database."""
    session = Session()
    try:
        words = session.query(FillerWord).order_by(FillerWord.word).all()
        if words:
            print(f"\n📋 Current filler words ({len(words)} total):")
            print("-" * 50)
            for idx, word_obj in enumerate(words, 1):
                print(f"{idx}. {word_obj.word}")
            print("-" * 50)
        else:
            print("\n❌ No filler words found in database.")
    finally:
        session.close()


def add_word():
    """Add a new filler word to the database."""
    word = input("\n✏️  Enter the filler word to add: ").strip().lower()

    if not word:
        print("❌ Error: Word cannot be empty!")
        return

    session = Session()
    try:
        # Check if word already exists
        existing = session.query(FillerWord).filter_by(word=word).first()
        if existing:
            print(f"⚠️  Word '{word}' already exists in database!")
        else:
            session.add(FillerWord(word=word))
            session.commit()
            print(f"✅ Successfully added '{word}' to the database!")
    except Exception as e:
        session.rollback()
        print(f"❌ Error adding word: {e}")
    finally:
        session.close()


def remove_word():
    """Remove a filler word from the database."""
    word = input("\n✏️  Enter the filler word to remove: ").strip().lower()

    if not word:
        print("❌ Error: Word cannot be empty!")
        return

    session = Session()
    try:
        # Find and delete the word
        result = session.query(FillerWord).filter_by(word=word).delete()
        session.commit()

        if result > 0:
            print(f"✅ Successfully removed '{word}' from the database!")
        else:
            print(f"⚠️  Word '{word}' not found in database!")
    except Exception as e:
        session.rollback()
        print(f"❌ Error removing word: {e}")
    finally:
        session.close()


def add_multiple_words():
    """Add multiple filler words at once (comma-separated)."""
    words_input = input("\n✏️  Enter filler words (comma-separated): ").strip()

    if not words_input:
        print("❌ Error: Input cannot be empty!")
        return

    words = [w.strip().lower() for w in words_input.split(",") if w.strip()]

    if not words:
        print("❌ Error: No valid words provided!")
        return

    session = Session()
    added_count = 0
    skipped_count = 0

    try:
        for word in words:
            # Check if word already exists
            existing = session.query(FillerWord).filter_by(word=word).first()
            if existing:
                print(f"⚠️  Skipped '{word}' (already exists)")
                skipped_count += 1
            else:
                session.add(FillerWord(word=word))
                added_count += 1

        session.commit()
        print(f"\n✅ Successfully added {added_count} word(s)!")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} word(s) (already existed)")
    except Exception as e:
        session.rollback()
        print(f"❌ Error adding words: {e}")
    finally:
        session.close()


def clear_all_words():
    """Clear all filler words from the database."""
    confirm = input("\n⚠️  Are you sure you want to delete ALL filler words? (yes/no): ").strip().lower()

    if confirm == "yes":
        session = Session()
        try:
            count = session.query(FillerWord).delete()
            session.commit()
            print(f"✅ Successfully deleted {count} filler word(s)!")
        except Exception as e:
            session.rollback()
            print(f"❌ Error clearing database: {e}")
        finally:
            session.close()
    else:
        print("❌ Operation cancelled.")


def main_menu():
    """Display the main menu and handle user choices."""
    while True:
        print("\n" + "=" * 50)
        print("🎤 FILLER WORDS DATABASE MANAGER")
        print("=" * 50)
        print("\n1. View all filler words")
        print("2. Add a single filler word")
        print("3. Add multiple filler words")
        print("4. Remove a filler word")
        print("5. Clear all filler words")
        print("6. Exit")
        print("-" * 50)

        choice = input("\n👉 Enter your choice (1-6): ").strip()

        if choice == "1":
            view_all_words()
        elif choice == "2":
            add_word()
        elif choice == "3":
            add_multiple_words()
        elif choice == "4":
            remove_word()
        elif choice == "5":
            clear_all_words()
        elif choice == "6":
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid choice! Please enter a number between 1-6.")


if __name__ == "__main__":
    print("\n🚀 Starting Filler Words Manager...")
    print("📁 Database: filler_words.db")

    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
