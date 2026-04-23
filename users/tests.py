from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile


class UserProfileTests(TestCase):
    """Test user profile views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create profile using get_or_create to avoid unique constraint
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.department = 'IT Department'
        self.profile.save()
    
    def test_profile_requires_login(self):
        """Test profile page requires login."""
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 302)
    
    def test_profile_view_get(self):
        """Test GET profile page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile_view'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], self.user)
    
    def test_edit_profile_requires_login(self):
        """Test edit profile requires login."""
        response = self.client.get(reverse('edit_profile'))
        self.assertEqual(response.status_code, 302)
    
    def test_edit_profile_get(self):
        """Test GET edit profile page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('edit_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_form', response.context)
        self.assertIn('profile_form', response.context)
    
    def test_edit_profile_post_valid(self):
        """Test editing profile with valid data."""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'username': 'testuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'newemail@example.com',
            'department': 'Support',
        }
        response = self.client.post(reverse('edit_profile'), data)
        
        # Verify redirect on successful edit
        self.assertEqual(response.status_code, 302)
        
        # Verify changes were saved
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.email, 'newemail@example.com')
        self.assertEqual(self.profile.department, 'Support')
    
    def test_change_password_requires_login(self):
        """Test change password requires login."""
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 302)
    
    def test_change_password_get(self):
        """Test GET change password page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
    
    def test_change_password_incorrect_current(self):
        """Test change password with incorrect current password."""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'current_password': 'wrongpassword',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123',
        }
        response = self.client.post(reverse('change_password'), data)
        self.assertEqual(response.status_code, 200)
    
    def test_change_password_mismatch(self):
        """Test change password with mismatched passwords."""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'confirm_password': 'differentpass123',
        }
        response = self.client.post(reverse('change_password'), data)
        self.assertEqual(response.status_code, 200)
    
    def test_change_password_valid(self):
        """Test changing password successfully."""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'current_password': 'testpass123',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123',
        }
        response = self.client.post(reverse('change_password'), data)
        
        # Should redirect on successful password change
        self.assertEqual(response.status_code, 302)
        
        # Verify password changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))
