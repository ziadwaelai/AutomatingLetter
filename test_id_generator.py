import unittest
from ai_generator import IDGenerator
import re
from datetime import datetime

class TestIDGenerator(unittest.TestCase):
    def test_id_format(self):
        """Test if the generated ID follows the correct format AIZ-YYYYMMDD-XXXX"""
        id_pattern = r'^AIZ-\d{8}-\d{4}$'
        for _ in range(100):  # Test multiple generations
            generated_id = IDGenerator.generate_id()
            self.assertTrue(re.match(id_pattern, generated_id), 
                          f"ID {generated_id} does not match the expected format")

    def test_id_date_component(self):
        """Test if the date component in the ID matches today's date"""
        today = datetime.now().strftime("%Y%m%d")
        generated_id = IDGenerator.generate_id()
        id_date = generated_id.split('-')[1]
        self.assertEqual(id_date, today, 
                        f"Date component {id_date} does not match today's date {today}")

    def test_id_randomness(self):
        """Test if the random component is within the expected range (0001-9999)"""
        for _ in range(100):  # Test multiple generations
            generated_id = IDGenerator.generate_id()
            random_component = int(generated_id.split('-')[2])
            self.assertTrue(1 <= random_component <= 9999,
                          f"Random component {random_component} is not within range 1-9999")

    def test_id_uniqueness(self):
        """Test if generated IDs are unique"""
        generated_ids = set()
        for _ in range(100):  # Test multiple generations
            generated_id = IDGenerator.generate_id()
            self.assertNotIn(generated_id, generated_ids,
                           f"Duplicate ID generated: {generated_id}")
            generated_ids.add(generated_id)

if __name__ == '__main__':
    unittest.main() 