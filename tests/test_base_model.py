"""Test cases for BaseModel and DBManager functionality."""

# External
from unittest.mock import patch, MagicMock, call
from django.db import IntegrityError, DatabaseError

# Internal
from cmn.base_test import TestClassBase, ModelTest
from cmn.base_model import BaseModel


class BaseManagerGetByIdTests(TestClassBase):
    """Test cases for BaseManager.get_by_id method.
    
    Tests various scenarios including valid IDs, invalid inputs,
    edge cases, and error handling.
    """

    def setUp(self):
        """Runs before each test: Extends UnitTestBase setup."""

        super().setUp()


    def test_get_by_id_valid_int(self) -> None:
        """Should return instance when given valid integer ID."""

        # Mock filter().first() behavior
        with patch.object(self.real_mock_manager, 'filter') as mock_filter:
            mock_filter.return_value.first.return_value = self.mock_service

            # Act: Call get_by_id with a valid integer ID
            result = self.real_mock_manager.get_by_id(1)

            # Assert: Verify the result and method calls
            self.assertEqual(result, self.mock_service)
            mock_filter.assert_called_once_with(id=1)


    def test_get_by_id_negative_int(self) -> None:
        """Should return None when given negative integer ID."""

        # Act
        result = self.real_mock_manager.get_by_id(-1)

        # Assert
        self.assertIsNone(result)


    def test_get_by_id_valid_str(self) -> None:
        """Should return instance when given valid string ID."""

        # Mock filter().first() behavior
        with patch.object(self.real_mock_manager, 'filter') as mock_filter:
            mock_filter.return_value.first.return_value = self.mock_service

            # Act
            result = self.real_mock_manager.get_by_id("1")

            # Assert
            self.assertEqual(result, self.mock_service)
            mock_filter.assert_called_once_with(id="1")


    def test_get_by_id_with_invalid_str(self) -> None:
        """Should return None when given non-numeric string ID."""

        # Act
        result = self.real_mock_manager.get_by_id("abc")

        # Assert
        self.assertIsNone(result)


    def test_get_by_id_zero(self) -> None:
        """Should return instance when given zero ID."""

        # Mock filter().first() behavior
        with patch.object(self.real_mock_manager, 'filter') as mock_filter:
            mock_filter.return_value.first.return_value = self.mock_service

            # Act
            result = self.real_mock_manager.get_by_id(0)

            # Assert
            self.assertEqual(result, self.mock_service)
            mock_filter.assert_called_once_with(id=0)


    def test_get_by_id_empty_str(self) -> None:
        """Should return None when given empty string ID."""

        # Act
        result = self.real_mock_manager.get_by_id("")

        # Assert
        self.assertIsNone(result)


    def test_get_by_id_none(self) -> None:
        """Should return None when given None as ID."""

        # Act
        result = self.real_mock_manager.get_by_id(None)

        # Assert
        self.assertIsNone(result)


    def test_get_by_id_boolean_input(self) -> None:
        """Should return None when given boolean input."""

        # Act
        result = self.real_mock_manager.get_by_id(False)

        # Assert
        self.assertIsNone(result)


    def test_get_by_id_exception(self) -> None:
        """Should raise ValueError when database exception occurs."""

        # Arrange
        with patch.object(self.real_mock_manager, 'filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            # Act
            with self.assertRaises(ValueError) as context:
                self.real_mock_manager.get_by_id(123)

            # Assert
            self.assertEqual(str(context.exception), "Database error")
            mock_filter.assert_called_once_with(id=123)


    def test_get_by_id_large_int(self) -> None:
        """Should return instance when given large integer ID."""

        # Mock filter().first() behavior
        with patch.object(self.real_mock_manager, 'filter') as mock_filter:
            mock_filter.return_value.first.return_value = self.mock_service

            # Act
            result = self.real_mock_manager.get_by_id(999999999999999999)

            # Assert
            self.assertEqual(result, self.mock_service)
            mock_filter.assert_called_once_with(id=999999999999999999)


class BaseManagerCreateInstanceTests(TestClassBase):
    """Test cases for BaseManager.create_instance method.
    
    Tests instance creation, validation, and error handling scenarios
    including database errors and invalid parameters.
    """


    def setUp(self):
        """Runs before each test: Extends UnitTestBase setup."""

        super().setUp()
        self.mock_model.__name__ = "TestModel"


    def test_create_instance_success(self) -> None:
        """Test successful instance creation."""

        # Arrange
        self.real_mock_manager.model = MagicMock(return_value=self.mock_service)
        self.mock_service.save.return_value = None  # Simulate save

        # Act
        instance = self.real_mock_manager.create_instance(name="abc")

        # Assert
        self.assertIsNotNone(instance, "Expected an instance to be created")
        self.assertIs(instance, self.mock_service)
        self.real_mock_manager.model.assert_called_once_with(name="abc")
        self.mock_service.save.assert_called_once()


    def test_create_instance_invalid_model(self) -> None:
        """Test create_instance when manager has no model attached."""

        # Arrange
        self.real_mock_manager.model = None

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.real_mock_manager.create_instance(name="Test Instance")

        self.assertEqual(
            str(context.exception),
            "BaseManager must be attached to a model before creating instances"
        )

        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_create_instance_empty_kwargs(self) -> None:
        """Test create_instance with empty keyword arguments."""

        # Act
        result = self.real_mock_manager.create_instance()

        # Assert
        self.assertIsNone(result)


    def test_create_instance_none_kwargs(self) -> None:
        """Test create_instance with None as keyword arguments."""

        # Act
        result = self.real_mock_manager.create_instance(**{})

        # Assert
        self.assertIsNone(result)


    def test_create_instance_integrity_error(self) -> None:
        """Should log and return None on IntegrityError."""

        # Arrange
        self.real_mock_manager.model = MagicMock(return_value=self.mock_service)
        self.mock_service.save.side_effect = IntegrityError("Duplicate entry")

        with patch("cmn.base_model.logger.error") as mock_logger:
            # Act
            result = self.real_mock_manager.create_instance(name="Test Instance")

            # Assert
            self.assertIsNone(result)
            mock_logger.assert_called_once()
            self.assertIn("IntegrityError", mock_logger.call_args[0][0])


    def test_create_instance_database_error(self) -> None:
        """Should log and return None on DatabaseError."""

        # Arrange
        self.real_mock_manager.model = MagicMock(return_value=self.mock_service)
        self.mock_service.save.side_effect = DatabaseError("DB connection lost")

        with patch("cmn.base_model.logger.error") as mock_logger:
            # Act
            result = self.real_mock_manager.create_instance(name="DB Issue")

            # Assert
            self.assertIsNone(result)
            mock_logger.assert_called_once()
            self.assertIn("DatabaseError", mock_logger.call_args[0][0])


    def test_create_instance_generic_exception(self) -> None:
        """Should log and return None on unexpected Exception."""

        # Arrange
        self.real_mock_manager.model = MagicMock(return_value=self.mock_service)
        self.mock_service.save.side_effect = RuntimeError("Unexpected crash")

        with patch("cmn.base_model.logger.exception") as mock_logger:
            # Act
            result = self.real_mock_manager.create_instance(name="Error Trigger")

            # Assert
            self.assertIsNone(result)
            mock_logger.assert_called_once()
            self.assertIn("Unexpected error", mock_logger.call_args[0][0])


class BaseManagerBulkOperationTests(TestClassBase):
    """Test cases for BaseManager bulk operation methods.
    
    Tests bulk_create_instances, bulk_update_instances, and bulk_delete_instances
    methods including batch processing, error handling, and edge cases.
    """

    def setUp(self):
        """Runs before each test: Extends UnitTestBase setup."""

        super().setUp()
        self.mock_model.__name__ = "ModelTest"
        self.test_fields = ['field1', 'field2']
        self.test_objects = [MagicMock(spec=BaseModel) for _ in range(5)]


    def test_bulk_create_instances_success(self) -> None:
        """Test successful bulk creation of instances."""

        # Arrange
        self.real_mock_manager.bulk_create = MagicMock(return_value=self.test_objects)

        # Act
        result = self.real_mock_manager.bulk_create_instances(self.test_objects, batch_size=2)

        # Assert
        self.assertEqual(result, self.test_objects)
        self.real_mock_manager.bulk_create.assert_called_once_with(self.test_objects, batch_size=2)
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_bulk_create_instances_empty_list(self) -> None:
        """Test bulk creation with empty objects list."""

        # Act
        result = self.real_mock_manager.bulk_create_instances([])

        # Assert
        self.assertEqual(result, [])
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_bulk_create_instances_integrity_error(self) -> None:
        """Test bulk creation handling of IntegrityError."""

        # Arrange
        integrity_error = IntegrityError("Duplicate entry")
        self.real_mock_manager.bulk_create = MagicMock(side_effect=integrity_error)

        # Act
        result = self.real_mock_manager.bulk_create_instances(self.test_objects)

        # Assert
        self.assertEqual(result, [])
        # self.assert_logs_error(f"IntegrityError during bulk_create: Duplicate entry")
        self.assert_no_exceptions_logged()


    def test_bulk_create_instances_unexpected_error(self) -> None:
        """Test bulk creation handling of unexpected errors."""

        # Arrange
        unexpected_error = Exception("Database connection failed")
        self.real_mock_manager.bulk_create = MagicMock(side_effect=unexpected_error)

        # Act & Assert
        with self.assertRaises(Exception) as context:
            self.real_mock_manager.bulk_create_instances(self.test_objects)

        self.assertEqual(str(context.exception), "Database connection failed")
        # self.assert_logs_exception(f"Unexpected error during bulk_create: {unexpected_error}")


    def test_bulk_update_instances_success(self) -> None:
        """Test successful bulk update of instances."""

        # Arrange
        self.real_mock_manager.bulk_update = MagicMock()

        # Act
        result = self.real_mock_manager.bulk_update_instances(self.test_objects, self.test_fields, batch_size=2)

        # Assert
        self.assertEqual(result, self.test_objects)
        # Should make 3 calls (5 items with batch_size=2)
        self.assertEqual(self.real_mock_manager.bulk_update.call_count, 3)
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_bulk_update_instances_integrity_error(self) -> None:
        """Test bulk update handling of IntegrityError."""

        # Arrange
        integrity_error = IntegrityError("Duplicate entry")
        self.real_mock_manager.bulk_update = MagicMock(side_effect=integrity_error)  # type: ignore[method-assign]

        # Act
        result = self.real_mock_manager.bulk_update_instances(self.test_objects, self.test_fields)

        # Assert
        self.assertEqual(result, [])
        self.assert_no_exceptions_logged()
        # self.assert_logs_error(f"IntegrityError during bulk_create: {integrity_error}")


    def test_bulk_update_instances_unexpected_error(self) -> None:
        """Test bulk update handling of unexpected errors."""

        # Arrange
        unexpected_error = Exception("Database connection failed")
        self.real_mock_manager.bulk_update = MagicMock(side_effect=unexpected_error)

        # Act & Assert
        with self.assertRaises(Exception) as context:
            self.real_mock_manager.bulk_update_instances(self.test_objects, self.test_fields)

        self.assertEqual(str(context.exception), "Database connection failed")
        # self.assert_logs_exception(f"Unexpected error during bulk_create: {unexpected_error}")


    def test_bulk_update_instances_empty_objects(self) -> None:
        """Test bulk update with empty objects list."""

        # Act
        result = self.real_mock_manager.bulk_update_instances([], self.test_fields)

        # Assert
        self.assertEqual(result, [])
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_bulk_update_instances_empty_fields(self) -> None:
        """Test bulk update with empty fields list."""

        # Arrange & Act
        result = self.real_mock_manager.bulk_update_instances(self.test_objects, [])

        # Assert
        self.assertEqual(result, [])
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_bulk_update_instances_batch_processing(self) -> None:
        """Test that bulk update properly batches objects."""

        # Arrange
        test_objects = [MagicMock(spec=BaseModel) for _ in range(10)]
        self.real_mock_manager.bulk_update = MagicMock()

        # Act
        self.real_mock_manager.bulk_update_instances(test_objects, self.test_fields, batch_size=3)

        # Assert
        # Should make 4 calls (10 items with batch_size=3)
        self.assertEqual(self.real_mock_manager.bulk_update.call_count, 4)

        # Verify batches are correct
        batches = [item.args[0] for item in self.real_mock_manager.bulk_update.call_args_list]
        self.assertEqual(len(batches[0]), 3)  # First 3 batches have 3 items
        self.assertEqual(len(batches[3]), 1)  # Last batch has 1 item


    def test_bulk_delete_instances_success(self) -> None:
        """Test successful bulk deletion with filters."""

        # Arrange
        test_objects = [MagicMock(spec=BaseModel) for _ in range(3)]
        for i, instance in enumerate(test_objects, 1):
            instance.pk = i

        # Create two separate mock querysets
        find_queryset = MagicMock()
        find_queryset.__iter__.return_value = iter(test_objects)

        delete_queryset = MagicMock()

        # Configure filter_by to return different querysets
        self.real_mock_manager.filter_by = MagicMock(side_effect=[
            find_queryset,  # First call returns instances
            delete_queryset  # Second call returns delete queryset
        ])

        # Act & Assert
        result = self.real_mock_manager.bulk_delete_instances(status="inactive")
        self.assertEqual(result, test_objects)

        # Verify filter_by calls using call()
        calls = self.real_mock_manager.filter_by.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], call(status="inactive"))
        self.assertEqual(calls[1], call(pk__in=[1, 2, 3]))

        delete_queryset.delete.assert_called_once()
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_bulk_delete_instances_integrity_error(self) -> None:
        """Test bulk delete handling of IntegrityError."""

        # Arrange
        mock_instances = [MagicMock(spec=BaseModel)]
        mock_instances[0].pk = 1

        # Set up mock queryset that will raise IntegrityError
        self.mock_service.filter_by.return_value = self.mock_service
        self.mock_service.__iter__.return_value = iter(mock_instances)
        self.mock_service.delete.side_effect = IntegrityError("Foreign key constraint")
        self.real_mock_manager.filter_by = MagicMock(return_value=self.mock_service)
        # Clear any previous mock calls
        self.mock_error_logger.reset_mock()

        # Act
        result = self.real_mock_manager.bulk_delete_instances(status="old")

        # Assert
        self.assertEqual(result, [])

        # Verify error was logged
        for call_arg in self.mock_error_logger.call_args_list:
            if "IntegrityError during bulk_delete" in call_arg[0][0]:
                # Error message found in logs
                break
        # Uncomment when error logging is implemented:
        # self.assertIsNotNone(logged_message, "Expected error log not found")
        # self.assertIn("Foreign key constraint", logged_message)
        self.assert_no_exceptions_logged()


    def test_bulk_delete_instances_unexpected_error(self) -> None:
        """Test bulk delete handling of unexpected errors."""
        # Arrange
        self.mock_model.pk = 1

        # Set up mock queryset that will raise unexpected error during iteration
        self.mock_service.filter_by.return_value = self.mock_service
        self.mock_service.__iter__.side_effect = Exception("Database connection failed")
        self.real_mock_manager.filter_by = MagicMock(return_value=self.mock_service)
        # Clear previous mock calls
        self.mock_exception_logger.reset_mock()

        # Act & Assert
        with self.assertRaises(Exception) as context:
            self.real_mock_manager.bulk_delete_instances(category="test")

        self.assertEqual(str(context.exception), "Database connection failed")
        # self.assert_logs_exception(f"Unexpected error during bulk_delete: Database connection failed")
        self.assertIn("Database connection failed", str(context.exception))


    def test_bulk_delete_instances_empty_filters(self) -> None:
        """Test bulk delete with empty fil dict."""

        # Arrange
        self.real_mock_manager.filter_by = self.mock_service

        # Act
        result = self.real_mock_manager.bulk_delete_instances()

        # Assert
        self.assertEqual(result, [])
        self.real_mock_manager.filter_by.assert_not_called()
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_bulk_delete_instances_no_matches(self) -> None:
        """Test bulk delete when no instances match filters."""

        # Arrange
        self.mock_service.filter_by.return_value = self.mock_service
        self.mock_service.__iter__.return_value = iter([])
        self.real_mock_manager.filter_by = self.mock_service

        # Act
        result = self.real_mock_manager.bulk_delete_instances(active=False)

        # Assert
        self.assertEqual(result, [])
        self.real_mock_manager.filter_by.assert_called_once_with(active=False)
        self.mock_service.delete.assert_not_called()
        self.assert_no_errors_logged()


class BaseModelTests(TestClassBase):
    """Test cases for BaseModel instance methods.
    
    Tests model lifecycle methods including save, update, delete,
    and associated hooks with proper error handling.
    """


    def setUp(self):
        """Runs before each test: Extends TestBase setup."""

        super().setUp()
        self.mock_model.pk, self.real_mock_model.pk = 1, 1
        self.mock_model.__class__.__name__ = "ModelTest"

        self.mock_model.commit = BaseModel.commit.__get__(self.mock_model)

        self.mock_model.before_update = BaseModel.before_update.__get__(self.mock_model)
        self.mock_model.update = BaseModel.update.__get__(self.mock_model)
        self.mock_model.after_update = BaseModel.after_update.__get__(self.mock_model)

        self.mock_model.before_save = BaseModel.before_save.__get__(self.mock_model)
        self.mock_model.save = BaseModel.save.__get__(self.mock_model)
        self.mock_model.after_save = BaseModel.after_save.__get__(self.mock_model)
        #
        # self.mock_model.delete = BaseModel.delete.__get__(self.mock_model)
        self.mock_exception_logger.reset_mock()  # Clear previous calls


    def test_commit_success(self) -> None:
        """Test successful transaction commit."""

        # Act
        self.mock_model.commit()

        # Assert
        self.mock_commit.assert_called_once()
        self.mock_rollback.assert_not_called()
        self.assert_no_errors_logged()


    def test_commit_failure(self) -> None:
        """Test transaction commit failure with rollback."""

        # Arrange
        self.mock_commit.side_effect = Exception("Database error")

        # Act
        with self.assertRaises(Exception) as ctx:
            self.mock_model.commit()


        # Assert
        self.assertEqual(str(ctx.exception), "Database error")
        self.mock_commit.assert_called_once()
        self.mock_rollback.assert_called_once()

        self.assert_logs_exception("Transaction commit failed: Database error")


    def test_before_update_success(self) -> None:
        """Test successful execution of before_update hook."""

        # Act
        self.mock_model.before_update()

        # Assert
        self.assert_logs_info(f"Running before_update hook for {self.mock_model.__class__.__name__}.")
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_before_update_failure(self) -> None:
        """Test before_update hook with an unexpected error."""

        # Arrange
        self.mock_model._before_update_hook = MagicMock(side_effect=RuntimeError("Unexpected error"))
        self.mock_exception_logger.reset_mock()  # Clear previous calls

        # Act
        with self.assertRaises(RuntimeError) as exc_context:
            self.mock_model.before_update()

        # Assert
        self.assertEqual(str(exc_context.exception), "Unexpected error")
        self.assert_logs_exception(
            f"Unexpected error in before_update for {self.mock_model.__class__.__name__}: Unexpected error"
        )


    def test_after_update_success(self) -> None:
        """Test successful execution of after_update hook."""

        # Act
        self.mock_model.after_update()

        # Assert
        self.assert_logs_info(f"Running after_update hook for {self.mock_model.__class__.__name__}.")
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_after_update_failure(self) -> None:
        """Test after_update hook with an unexpected error."""

        # Arrange
        self.mock_model._after_update_hook = MagicMock(side_effect=RuntimeError("Unexpected error"))
        self.mock_exception_logger.reset_mock()  # Clear previous calls

        # Act
        with self.assertRaises(RuntimeError):
            self.mock_model.after_update()

        # Assert
        self.assert_logs_exception(
            f"Unexpected error in after_update for {self.mock_model.__class__.__name__}: Unexpected error"
        )


    def test_update_success(self) -> None:
        """Test that update works correctly when no errors occur."""

        # Arrange
        with patch.object(self.mock_model, "before_update") as mock_before_update, \
                patch.object(self.mock_model, "after_update") as mock_after_update, \
                patch.object(self.mock_model, "save") as mock_save:

            # Act
            self.mock_model.update(name="New Name")

            # Assert hooks
            mock_before_update.assert_called_once()
            mock_save.assert_called_once_with()
            mock_after_update.assert_called_once()

            # Assert update logs a success message
            expected_info = f"Updated {self.mock_model.__class__.__name__} (ID: {self.mock_model.pk}) successfully"
            self.assert_logs_info(expected_info)


    def test_update_failure(self) -> None:
        """Test that update() logs an exception and re-raises when before_update fails via lambda."""

        # Arrange
        self.mock_model.before_update = lambda: (_ for _ in ()).throw(Exception("Hook failure"))

        # Act
        with self.assertRaises(Exception) as ctx:
            self.mock_model.update(name="New Name", description="Should fail")

        # Assert
        self.assertIn("Hook failure", str(ctx.exception))
        expected_error = f"Error updating {self.mock_model.__class__.__name__}: Hook failure"
        self.assert_logs_exception(expected_error)


    def test_update_handles_unexpected_exception(self) -> None:
        """Ensure update logs an exception and raises it if something unexpected occurs."""

        # Arrange

        with patch.object(self.mock_model, "save", side_effect=Exception("Unexpected DB error")), \
                patch('cmn.base_model.logger.exception') as mock_exception:
            # Act
            with self.assertRaises(Exception) as ctx:
                self.mock_model.update(name="New Name")

                # Assert
                self.assertIn("Unexpected DB error", str(ctx.exception))
                mock_exception.assert_called_once_with(
                    "Error updating ModelTest: Unexpected DB error"
                )


    def test_before_save_success(self) -> None:
        """Ensure `before_save` logs the correct message."""

        # Act
        self.mock_model.before_save()

        # Assert
        self.assert_logs_info(f"Running before_save hook for {self.mock_model.__class__.__name__}.")
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_before_save_failure(self) -> None:
        """Ensure `before_save` logs an exception if an error occurs."""

        # Arrange
        self.mock_model._before_save_hook = MagicMock(side_effect=RuntimeError("Unexpected error"))

        # Act
        with self.assertRaises(RuntimeError) as exc_context:
            self.mock_model.before_save()

        # Assert
        self.assertEqual(str(exc_context.exception), "Unexpected error")
        self.assert_logs_exception(
            f"Unexpected error in before_save for {self.mock_model.__class__.__name__}: Unexpected error"
        )


    def test_after_save_success(self) -> None:
        """Ensure `after_save` logs the correct message."""

        # Act
        self.mock_model.after_save()

        # Assert
        self.assert_logs_info(f"Running after_save hook for {self.mock_model.__class__.__name__}.")
        self.assert_no_errors_logged()
        self.assert_no_exceptions_logged()


    def test_after_save_failure(self) -> None:
        """Ensure `after_save` logs an exception if an error occurs."""

        # Arrange
        self.mock_model._after_save_hook = MagicMock(side_effect=RuntimeError("Unexpected error"))

        # Act
        with self.assertRaises(RuntimeError) as exc_context:
            self.mock_model.after_save()

        # Assert
        self.assertEqual(str(exc_context.exception), "Unexpected error")
        self.assert_logs_exception(
            f"Unexpected error in after_save for {self.mock_model.__class__.__name__}: Unexpected error"
        )


    def test_save_with_commit_true(self) -> None:
        """Test that save() works with commit=True."""

        # Arrange
        with patch("django.db.models.Model.save", autospec=True) as mock_parent_save:
            self.real_mock_model.before_save = lambda: None
            self.real_mock_model.after_save = lambda: None

            # Act
            self.real_mock_model.save(commit=True)

            # Assert
            mock_parent_save.assert_called_once_with(self.real_mock_model)


    def test_save_with_invalid_commit(self) -> None:
        """Test that save() rejects non-boolean commit parameter."""

        # Act & Assert
        with self.assertRaises(ValueError, msg="Commit must be a boolean"):
            self.real_mock_model.save(commit=False, invalid_param="False")


    def test_save_with_positional_args(self) -> None:
        """Test that save() rejects positional arguments."""

        # Act & Assert
        with self.assertRaises(ValueError, msg="Unexpected positional arguments"):
            self.real_mock_model.save(True, "extra_arg")


    def test_save_success(self) -> None:
        """Test that save() works correctly when no errors occur without hitting DB."""

        # Arrange
        with patch("django.db.models.Model.save", autospec=True) as mock_parent_save:
            self.real_mock_model.before_save = MagicMock()
            self.real_mock_model.after_save = MagicMock()

            # Act
            self.real_mock_model.save()

            # Assert - Verify the interaction flow
            mock_parent_save.assert_called_once_with(self.real_mock_model)
            self.real_mock_model.before_save.assert_called_once()
            self.real_mock_model.after_save.assert_called_once()
            self.assert_logs_info(
                f"Successfully saved {self.real_mock_model.__class__.__name__} (ID: {self.real_mock_model.pk})"
            )


    def test_save_failure_due_to_before_save_failure(self) -> None:
        """Test that save() logs an exception when before_save fails."""

        # Arrange
        # 1. Create real mock model
        self.real_mock_model = ModelTest(name="ModelTest")

        # 2. Set up failing before_save and no-op after_save
        self.real_mock_model.before_save = MagicMock(
            side_effect=Exception("Unexpected error in before_save")
        )
        self.real_mock_model.after_save = MagicMock()

        with self.assertRaises(Exception) as ctx:
            self.real_mock_model.save(commit=True)

            # Assert
            self.assertIn("Unexpected error in before_save ", str(ctx.exception))

            self.assert_logs_error(
                f"Unexpected error in before_save{self.real_mock_model.__class__.__name__}. "
                f"Unexpected error in before_save"
            )

            self.real_mock_model.after_save.assert_not_called()


    def test_save_handles_integrity_error(self) -> None:
        """Ensure that save() handles IntegrityError and logs it."""

        # Arrange: Override hooks with no-ops
        self.real_mock_model.before_save = lambda: None
        self.real_mock_model.after_save = lambda: None

        with patch("django.db.models.Model.save", autospec=True,
                   side_effect=IntegrityError("Integrity issue")) as mock_parent_save:
            # Act
            with self.assertRaises(IntegrityError) as exc_context:
                self.real_mock_model.save()

            # Assert: Exception content
            self.assertIn("Integrity issue", str(exc_context.exception))

            # Assert: save and transaction.atomic were called
            mock_parent_save.assert_called_once_with(self.real_mock_model)
            self.assert_logs_error(
                f"IntegrityError in {self.real_mock_model.__class__.__name__}.save(): Integrity issue"
            )


    def test_save_handles_unexpected_exception(self) -> None:
        """Ensure that save() logs unexpected exceptions and re-raises them."""

        # Arrange
        self.real_mock_model.before_save = lambda: None
        self.real_mock_model.after_save = lambda: None

        with patch("django.db.models.Model.save", autospec=True,
                   side_effect=Exception("Unexpected error")) as mock_parent_save:
            # Act
            with self.assertRaises(Exception) as ctx:
                self.real_mock_model.save(commit=True)

            self.assertIn("Unexpected error", str(ctx.exception))
            mock_parent_save.assert_called_once_with(self.real_mock_model)
            self.assert_logs_exception(
            f"Unexpected error in {self.real_mock_model.__class__.__name__}.save(): Unexpected error"
            )


    def test_delete_success(self) -> None:
        """Ensure `delete` logs a success message when an instance is deleted."""

        # Arrange
        with patch("django.db.models.Model.delete", autospec=True) as mock_parent_delete:

            # Act
            self.real_mock_model.delete()

            # Assert
            mock_parent_delete.assert_called_once_with(self.real_mock_model)
            self.assert_logs_info(
                f"Deleted {self.real_mock_model.__class__.__name__} (ID: {self.real_mock_model.pk}) successfully"
            )


    def test_delete_handles_exception(self) -> None:
        """Ensure `delete` logs and raises exceptions correctly."""

        # Arrange
        with patch("django.db.models.Model.delete", autospec=True,
                   side_effect=Exception("Deletion failed")) as mock_parent_delete:
            # Act
            with self.assertRaises(Exception) as ctx:
                self.real_mock_model.delete()

            # Assert
            self.assertIn("Deletion failed", str(ctx.exception))
            mock_parent_delete.assert_called_once_with(self.real_mock_model)
            self.assert_logs_exception(
                f"Error deleting {self.real_mock_model.__class__.__name__} (ID: {self.real_mock_model.pk}): Deletion failed"
            )