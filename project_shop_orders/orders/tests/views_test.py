from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework import status

from django.test import TestCase
from your_app.models import ConfirmEmailToken

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from .views import YourAPIView  # Import your API view class

import json

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from rest_framework.authtoken.models import Token
from orders.models import Contact
from orders.api.views import ContactView
from orders.api.serializers import ContactSerializer

from project_shop_orders.orders.api.views import ShopStateView

from .views import YourView

from .models import Product  # Import your Product model
from .serializers import ProductSerializer  # Import your ProductSerializer

from rest_framework import status
from django.contrib.auth import get_user_model



class PartnerOrdersTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_authenticate(user=self.user)

    def test_get_orders_for_shop_user(self):
        url = reverse('partner-orders')  # Assuming you have a URL name for the PartnerOrders view
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Add more assertions based on the expected behavior of the get method



class RegisterUserTests(APITestCase):
    def test_valid_data(self):
        url = reverse('register-user')  # Adjust this URL name based on your project's URL configuration
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'StrongPassword123',
            'company': 'Example Company',
            'position': 'Developer'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Add more assertions to validate the response data



class ConfirmEmailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('confirm_email')
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword',
            is_active=False
        )
        self.token = ConfirmEmailToken.objects.create(
            user=self.user,
            key='testtoken'
        )

    def test_confirm_email_with_valid_token(self):
        data = {
            'email': self.user.email,
            'token': self.token.key
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['Status'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(ConfirmEmailToken.objects.filter(user=self.user).exists())

    def test_confirm_email_with_invalid_token(self):
        data = {
            'email': self.user.email,
            'token': 'invalidtoken'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['Status'])
        self.assertEqual(response.data['Errors'], 'Неправильно указан token или email')

    def test_confirm_email_with_invalid_email(self):
        data = {
            'email': 'invalid@example.com',
            'token': self.token.key
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['Status'])
        self.assertEqual(response.data['Errors'], 'Неправильно указан token или email')

    def test_confirm_email_with_missing_data(self):
        data = {}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['Status'])
        self.assertEqual(response.data['Errors'], 'Не указаны все аргументы')




class TestYourAPIView(TestCase):

    def test_valid_authentication(self):
        factory = APIRequestFactory()
        data = {'email': 'test@example.com', 'password': 'test_password'}
        request = factory.post('/your-api-endpoint/', data)

        # You would need to adjust the assertions based on your actual implementation
        response = YourAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['status'])

    def test_invalid_authentication(self):
        factory = APIRequestFactory()
        data = {'email': 'invalid@example.com', 'password': 'invalid_password'}
        request = factory.post('/your-api-endpoint/', data)

        # You would need to adjust the assertions based on your actual implementation
        response = YourAPIView.as_view()(request)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data['status'])



class TestUserPost(APITestCase):

    def test_valid_password(self):
        url = reverse('user-post')  # Assuming you have a URL name for the post method
        data = {'password': 'valid_password'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_password(self):
        url = reverse('user-post')  # Assuming you have a URL name for the post method
        data = {'password': 'short'}  # Assuming 'short' is an invalid password
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)




class ContactViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.contact = Contact.objects.create(user=self.user, city='City', street='Street', phone='1234567890')
        self.token = Token.objects.create(user=self.user)

    def test_get_contacts(self):
        request = self.factory.get('/contacts')
        request.user = self.user
        view = ContactView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_contact(self):
        data = {'id': self.contact.id, 'city': 'New City'}
        request = self.factory.put('/contacts', data=data)
        request.user = self.user
        view = ContactView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(Contact.objects.get(id=self.contact.id).city, 'New City')

    def test_delete_contact(self):
        data = {'items': str(self.contact.id)}
        request = self.factory.delete('/contacts', data=data)
        request.user = self.user
        view = ContactView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(Contact.objects.count(), 0)

    def test_delete_contacts(self):
        contact2 = Contact.objects.create(user=self.user, city='City 2', street='Street 2', phone='0987654321')
        data = {'items': '{},{}'.format(self.contact.id, contact2.id)}
        request = self.factory.delete('/contacts', data=data)
        request.user = self.user
        view = ContactView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(Contact.objects.count(), 0)

    def test_update_contact_invalid_id(self):
        data = {'id': 'invalid_id', 'city': 'New City'}
        request = self.factory.put('/contacts', data=data)
        request.user = self.user
        view = ContactView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Не верный тип поля ID')

    def test_delete_contact_invalid_id(self):
        data = {'items': 'invalid_id'}
        request = self.factory.delete('/contacts', data=data)
        request.user = self.user
        view = ContactView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Не верный тип поля')




class ShopStateViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_get(self):
        request = self.factory.get('/shop/state/')
        request.user = self.user

        view = ShopStateView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': self.shop.state})

    def test_post(self):
        request = self.factory.post('/shop/state/', {'state': 'True'})
        request.user = self.user

        view = ShopStateView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': True})

        # test that the state was updated in the database
        self.shop.refresh_from_db()
        self.assertTrue(self.shop.state)

        # test that an error is returned if the state is not provided
        request = self.factory.post('/shop/state/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'status': False, 'error': 'Не указано поле Статус'})

        # test that an error is returned if the state is not a boolean
        request = self.factory.post('/shop/state/', {'state': 'not a boolean'})
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'status': False, 'error': 'Некорректное значение поля Статус'})

        # test that an error is returned if the user is not a shop
        request.user.type = 'not a shop'
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {'status': False, 'error': 'Только для магазинов'})




class YourViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.user.type = 'shop'
        self.user.save()

    def test_post_valid_data(self):
        data = {'url': 'http://example.com/data.yaml'}
        request = self.factory.post('/your-url/', data, format='json')
        request.user = self.user
        response = YourView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data, {'status': True})

    def test_post_invalid_url(self):
        data = {'url': 'not a url'}
        request = self.factory.post('/your-url/', data, format='json')
        request.user = self.user
        response = YourView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'status': False, 'error': 'Enter a valid URL.'})

    def test_post_user_not_shop(self):
        data = {'url': 'http://example.com/data.yaml'}
        request = self.factory.post('/your-url/', data, format='json')
        request.user = User.objects.create_user(username='notashop', password='testpassword')
        response = YourView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {'status': False, 'error': 'Только для магазинов'})

    def test_post_missing_data(self):
        request = self.factory.post('/your-url/', {}, format='json')
        request.user = self.user
        response = YourView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'status': False, 'error': 'Не указаны все необходимые поля'})




class ProductViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('product-list')  # Assuming you have a URL name for the ProductView

    def test_get_product_list(self):
        # Create some test data
        product1 = Product.objects.create(name='Test Product 1', )
        product2 = Product.objects.create(name='Test Product 2', )

        # Make GET request to fetch the product list
        response = self.client.get(self.url)

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Serialize the queryset to compare with the response data
        queryset = Product.objects.all()
        serializer = ProductSerializer(queryset, many=True)

        # Check if the response data matches the serialized queryset
        self.assertEqual(response.data, serializer.data)




User = get_user_model()

class OrderViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

    def test_get_orders(self):
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Add more assertions based on the expected behavior

    def test_create_order(self):
        url = reverse('order-list')
        data = {'id': 1, 'contact': 1}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Add more assertions based on the expected behavior