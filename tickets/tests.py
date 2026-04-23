"""Test suite for tickets app."""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Ticket
from .forms import TicketForm
from .security import validate_ticket_title, validate_feedback_text
from django.core.exceptions import ValidationError


class TicketModelTests(TestCase):
    """Test the Ticket model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.ticket = Ticket.objects.create(
            owner=self.user,
            title="Cannot connect to network",
            description="My computer cannot connect to WiFi",
            category="Network",
            priority="High",
            suggested_solution="Check if WiFi is enabled"
        )
    
    def test_ticket_creation(self):
        """Test creating a ticket."""
        self.assertEqual(self.ticket.title, "Cannot connect to network")
        self.assertEqual(self.ticket.owner, self.user)
    
    def test_mark_helpful(self):
        """Test marking ticket as helpful."""
        self.ticket.mark_ai_solution_helpful(feedback_text="It worked!")
        self.ticket.refresh_from_db()
        
        self.assertTrue(self.ticket.ai_solution_helpful)
        self.assertTrue(self.ticket.resolved_by_ai)
    
    def test_mark_unhelpful(self):
        """Test marking ticket as unhelpful."""
        self.ticket.mark_ai_solution_unhelpful(feedback_text="Didn't work")
        self.ticket.refresh_from_db()
        
        self.assertFalse(self.ticket.ai_solution_helpful)


class TicketFormTests(TestCase):
    """Test form validation."""
    
    def test_valid_form(self):
        """Test valid form submission."""
        form = TicketForm(data={
            'title': 'Cannot access email',
            'description': 'I cannot access my email through Outlook'
        })
        self.assertTrue(form.is_valid())
    
    def test_empty_title(self):
        """Test form rejects empty title."""
        form = TicketForm(data={
            'title': '',
            'description': 'Valid description'
        })
        self.assertFalse(form.is_valid())
    
    def test_short_title(self):
        """Test form rejects short title."""
        form = TicketForm(data={
            'title': 'Bad',
            'description': 'Valid description here'
        })
        self.assertFalse(form.is_valid())
    
    def test_short_description(self):
        """Test rejects short description."""
        form = TicketForm(data={
            'title': 'Valid title',
            'description': 'Short'
        })
        self.assertFalse(form.is_valid())
    
    def test_sql_injection_attempt(self):
        """Test form rejects SQL injection."""
        form = TicketForm(data={
            'title': "'; DROP TABLE--",
            'description': 'This is a description'
        })
        self.assertFalse(form.is_valid())
    
    def test_identical_title_desc(self):
        """Test form rejects when title = description."""
        # Use longer identical strings to pass length validation
        identical = "This is a longer description that meets minimum length requirements"
        form = TicketForm(data={
            'title': identical,
            'description': identical
        })
        self.assertFalse(form.is_valid())


class SecurityTests(TestCase):
    """Test security validation."""
    
    def test_valid_title(self):
        """Test valid title."""
        title = validate_ticket_title("Cannot access email")
        self.assertIsNotNone(title)
    
    def test_null_bytes(self):
        """Test null bytes are rejected."""
        with self.assertRaises(ValidationError):
            validate_ticket_title("Title\x00 with null byte")
    
    def test_feedback_validation(self):
        """Test feedback validation."""
        feedback = validate_feedback_text("Thank you!")
        self.assertEqual(feedback, "Thank you!")
    
    def test_feedback_too_long(self):
        """Test feedback over limit is rejected."""
        with self.assertRaises(ValidationError):
            validate_feedback_text("a" * 1001)


class TicketViewTests(TestCase):
    """Test ticket views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.ticket = Ticket.objects.create(
            owner=self.user,
            title="Cannot connect to network",
            description="My computer cannot connect to WiFi",
            category="Network",
            priority="High",
            suggested_solution="Check WiFi"
        )
    
    def test_create_requires_login(self):
        """Test create page requires login."""
        response = self.client.get(reverse('create_ticket'))
        self.assertEqual(response.status_code, 302)
    
    def test_create_get(self):
        """Test GET create ticket page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('create_ticket'))
        self.assertEqual(response.status_code, 200)
    
    def test_create_post_valid(self):
        """Test creating ticket with valid data."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('create_ticket'), {
            'title': 'Printer not working',
            'description': 'The printer is not responding to network requests'
        })
        # Successful creation returns template with created ticket info
        self.assertEqual(response.status_code, 200)
        # Verify ticket was created
        self.assertTrue(Ticket.objects.filter(title='Printer not working').exists())
    
    def test_detail_requires_login(self):
        """Test detail page requires login."""
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.id]))
        self.assertEqual(response.status_code, 302)
    
    def test_detail_owner_can_view(self):
        """Test owner can view ticket."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_mark_helpful_requires_login(self):
        """Test mark helpful requires login."""
        response = self.client.post(
            reverse('mark_ai_helpful', args=[self.ticket.id]),
            {'feedback': 'It worked!'}
        )
        self.assertEqual(response.status_code, 302)
    
    def test_mark_helpful_owner(self):
        """Test marking ticket helpful."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('mark_ai_helpful', args=[self.ticket.id]),
            {'feedback': 'Great!'}
        )
        self.assertEqual(response.status_code, 200)
        
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.ai_solution_helpful)


class TicketCommentTests(TestCase):
    """Test comment functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        self.ticket = Ticket.objects.create(
            owner=self.user,
            title="Test ticket",
            description="Test description",
            category="Software",
            priority="Medium",
            suggested_solution="Test solution"
        )
    
    def test_add_comment_requires_login(self):
        """Test adding comment requires login."""
        response = self.client.post(
            reverse('add_comment', args=[self.ticket.id]),
            {'text': 'Test comment'}
        )
        self.assertEqual(response.status_code, 302)
    
    def test_add_comment_on_own_ticket(self):
        """Test owner can add comment to ticket."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('add_comment', args=[self.ticket.id]),
            {'text': 'This is a test comment with some helpful info'}
        )
        self.assertEqual(response.status_code, 302)
        
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.comments.count(), 1)
        self.assertEqual(
            self.ticket.comments.first().text,
            'This is a test comment with some helpful info'
        )
    
    def test_delete_comment_author_only(self):
        """Test only author can delete comment."""
        from .models import TicketComment
        
        comment = TicketComment.objects.create(
            ticket=self.ticket,
            author=self.user,
            text='Test comment to delete'
        )
        
        # Other user cannot delete
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.post(
            reverse('delete_comment', args=[comment.id])
        )
        self.assertEqual(response.status_code, 302)
        
        # Comment should still exist
        self.assertTrue(TicketComment.objects.filter(id=comment.id).exists())
        
        # Author can delete
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('delete_comment', args=[comment.id])
        )
        self.assertEqual(response.status_code, 302)
        
        # Comment should be gone
        self.assertFalse(TicketComment.objects.filter(id=comment.id).exists())


class BasicCoverageTests(TestCase):
    """Essential model, auth, and AI integration coverage."""

    def test_ticket_creation(self):
        user = User.objects.create_user(username='basic_test', password='1234')
        ticket = Ticket.objects.create(
            owner=user,
            title='Test Issue',
            description='Test description'
        )
        self.assertEqual(ticket.title, 'Test Issue')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_logged_in_staff_can_access_dashboard(self):
        user = User.objects.create_user(
            username='admin_test',
            password='1234',
            is_staff=True
        )
        self.client.login(username='admin_test', password='1234')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_ai_solution_saved(self):
        user = User.objects.create_user(username='ai_test', password='1234')
        self.client.login(username='ai_test', password='1234')

        response = self.client.post(reverse('create_ticket'), {
            'title': 'wifi not working',
            'description': 'wifi not connecting'
        })

        self.assertEqual(response.status_code, 200)
        ticket = Ticket.objects.last()
        self.assertIsNotNone(ticket)
        self.assertIsNotNone(ticket.suggested_solution)
        self.assertNotEqual((ticket.suggested_solution or '').strip(), '')

    def test_mark_resolved(self):
        staff = User.objects.create_user(
            username='resolver',
            password='1234',
            is_staff=True
        )
        owner = User.objects.create_user(username='owner_user', password='1234')
        self.client.login(username='resolver', password='1234')

        ticket = Ticket.objects.create(
            owner=owner,
            title='Test',
            description='Test description for resolution flow'
        )

        self.client.post(reverse('resolve_ticket', args=[ticket.id]), {
            'status': 'Resolved',
            'feedback': 'Resolved in test flow'
        })
        ticket.refresh_from_db()
        self.assertEqual(ticket.resolution_status, 'Resolved')


