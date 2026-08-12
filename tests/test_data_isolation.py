"""Tests that this app does not share data with other local apps or repos."""

import unittest

import data_storage


class DataIsolationTests(unittest.TestCase):
    def test_data_directory_is_unique_to_this_app(self):
        self.assertEqual(data_storage.APP_DATA_NAME, "ToDoDesktop")
        self.assertEqual(data_storage.get_data_directory().name, "ToDoDesktop")
        self.assertNotEqual(data_storage.get_data_directory().name, "ToDo")

    def test_habit_tracker_apis_are_not_exported(self):
        self.assertFalse(hasattr(data_storage, "load_habits"))
        self.assertFalse(hasattr(data_storage, "save_habits"))
        self.assertFalse(hasattr(data_storage, "HABITS_FILE"))
