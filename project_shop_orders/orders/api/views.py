from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.db.models import Sum, Q, Prefetch
from django.core.mail import EmailMessage
from requests import get
from rest_framework import status, generics, viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from .models import *
from .serializers import *
from yaml import load as load_yaml, Loader
from ujson import loads as load_json
from distutils.util import strtobool
from api.tasks import send_email, get_import
from drf_spectacular.utils import extend_schema

# Create your views here.

def on_change_order_status(user_id, order_id):
    """Функция отправит пользователю письмо об изменении статуса заказа
    Аргументы:
        user_id (int): Идентификатор пользователя.
        order_id (int): Идентификатор заказа.

    Возвращает:
        None
    """
    # Получаем пользователя и заказ из базы данных
    user = User.objects.get(id=user_id)
    order = Order.objects.get(id=order_id)
    # Создаем текст письма
    message = 'Твой заказ номер {} имеет статус "{}"'.format(
        order_id,
        order.status.upper())
    # Устанавливаем получателя и тему письма
    to_email = user.email
    mail_subject = 'Статус заказа изменен'
    # Создаем и отправляем письмо
    email = EmailMessage(mail_subject, message, to=[to_email])
    email.send()


class ApiListPagination(PageNumberPagination):
    """ Класс пагинации
    page_size определяет количество объектов, которые будут отображаться на одной странице.
    Здесь установлено значение 3.
    page_size_query_param определяет имя параметра запроса, который будет использоваться
    для установки количества объектов на странице. Здесь установлено значение 'page_size'.
    max_page_size определяет максимальное количество объектов, которые могут быть отображены
    на одной странице. Здесь установлено значение 10000.
    Этот класс используется для реализации пагинации в API. User
    """
    page_size = 3
    page_size_query_param = 'page_size'
    max_page_size = 10000


class RegisterUser(APIView):
    """Класс для регистрации покупателя"""
    """
    Process a POST request and create a new user.
    Args:
        request (Request): The Django request object.
    Returns:
        Response: The response indicating the status of the operation and any errors.
    """
    throttle_scope = 'register'

    def post(self, request, *args, **kwargs):
        # проверяем обязательные аргументы
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as error:
                return Response({'status': False, 'error': {'password': error}}, status=status.HTTP_403_FORBIDDEN)
            else:
                # проверяем данные для уникальности имени пользователя
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
                    return Response({'status': True, 'token for confirm email': token.key})
                else:
                    return Response({'status': False, 'error': user_serializer.errors}, status=status.HTTP_403_FORBIDDEN
                                    )

        return Response({'status': False, 'error': 'Не указаны все поля'}, status=status.HTTP_400_BAD_REQUEST)


class Сonfirmation(APIView):
    """Класс для подтверждения регистрации""" 
    def post(self, request, *args, **kwargs):
        """
            Подтверждает почтовый адрес пользователя.
            Args:
                - request (Request): The Django request object.
            Returns:
                - Response: The response indicating the status of the operation and any errors.
        """
        # проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return Response({
                    'Status': True
                })
            else:
                return Response({'Status': False, 'Errors': 'Неправильно указан token или email'})
        return Response({'Status': False, 'Errors': 'Не указыны все аргументы'}) 


class LoginUser(APIView):
    """Класс для входа(авторизации)"""

    # Авторизация методом POST
    def post(self, request, *args, **kwargs):
        """
           Authenticate a user.
           Args:
                request (Request): The Django request object.
           Returns:
                Response: The response indicating the status of the operation and any errors.
        """
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return Response({'status': True, 'token': token.key})
            return Response({'status': False, 'error': 'Ошибка входа'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status': False, 'error': 'Не указаны все поля'}, status=status.HTTP_400_BAD_REQUEST)


class DetailUser(APIView):
    """Класс для просмотра и изменения данных пользователя"""
    """
        A class for managing user account details.
        Methods:
        - get: Retrieve the details of the authenticated user.
        - post: Update the account details of the authenticated user.
        Attributes:
        - None
    """
    permission_classes = [IsAuthenticated]

    # получить данные
    def get(self, request, *args, **kwargs):
        """
            Retrieve the details of the authenticated user.
            Args:
                - request (Request): The Django request object.
            Returns:
                - Response: The response containing the details of the authenticated user.
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом POST
    def post(self, request, *args, **kwargs):
        """
            Update the account details of the authenticated user.
            Args:
                - request (Request): The Django request object.
            Returns:
                - Response: The response indicating the status of the operation and any errors.
        """
        # проверяем обязательные аргументы
        if {'password'}.issubset(request.data):
            if 'password' in request.data:
                try:
                    validate_password(request.data['password'])
                except Exception as error:
                    return Response({'status': False, 'error': {'password': error}}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    request.user.set_password(request.data['password'])
            # проверяем остальные данные
            user_serializer = UserSerializer(request.user, data=request.data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
                return Response({'status': True}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'status': False, 'Errors': 'Не указаны все арументы'})


class UserViewSet(viewsets.ModelViewSet):
    """
    API-точка, позволяющая просматривать или редактировать пользователей.
    """
    # Запрос всех объектов пользователя
    queryset = User.objects.all()
    # Класс сериализатора для модели пользователя
    serializer_class = UserSerializer


class ContactView(APIView):
    """
        A class for managing contact information.

        Methods:
           - get: Retrieve the contact information of the authenticated user.
           - put: Update the contact information of the authenticated user.
           - delete: Delete the contact of the authenticated user.
        Attributes:
           - None
    """
    """
        Код в указанном блоке представляет собой класс ,
        который отвечает за управление контактной информацией пользователя.
        Метод [get] используется для получения контактной информации авторизованного
        пользователя. Он проверяет, что пользователь авторизован, затем выбирает 
        контактные данные из базы данных, связанные с текущим пользователем, и
        сериализует их для возврата в ответе.
        Метод [delete] используется для удаления контакта авторизованного пользователя.
        Он также проверяет, что пользователь авторизован, затем получает данные из 
        запроса в формате JSON. Если данные корректны, он удаляет контакт, связанный 
        с текущим пользователем, и возвращает ответ с информацией о статусе и количестве
        удаленных объектов.
        Метод [put] используется для обновления контактной информации авторизованного 
        пользователя. Он также проверяет, что пользователь авторизован, затем получает
        данные из запроса в формате JSON. Если данные корректны, он обновляет контактную
        информацию, связанную с текущим пользователем, и возвращает ответ с информацией
       о статусе.
       В целом, класс ContactView предоставляет API для управления контактной информацией
       пользователя, включая создание, чтение, обновление и удаление контактов.  
        """
    permission_classes = [IsAuthenticated]

    # получить мои контакты
    def get(self, request, *args, **kwargs):
        """Функция получения контактных данных"""
        """
            Retrieve the contact information of the authenticated user.
            Args:
                - request (Request): The Django request object.
            Returns:
                - Response: The response containing the contact information.
        """
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)

    # редактировать контакт
    def put(self, request, *args, **kwargs):
        """Метод изменения контакта"""
        """
            Update the contact information of the authenticated user.
            Args:
                - request (Request): The Django request object
            Returns:
                - Response: The response indicating the status of the operation and any errors.
        """
        if {'id'}.issubset(request.data):
            try:
                contact = Contact.objects.get(pk=int(request.data['id']))
            except ValueError:
                return Response({'status': False, 'error': 'Не верный тип поля ID'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = ContactSerializer(contact, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'status': True}, status=status.HTTP_200_OK)
            return Response({'status': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': False, 'error': 'Не указаны необходимые поля'}, status=status.HTTP_400_BAD_REQUEST)

    # удалить контакт
    def delete(self, request, *args, **kwargs):
        """Функция удаления контакта"""
        """
            Delete the contact of the authenticated user.
            Args:
                - request (Request): The Django request object.
            Returns:
                - Response: The response indicating the status of the operation and any errors.
        """
        if {'items'}.issubset(request.data):
            for item in request.data["items"].split(','):
                try:
                    contact = Contact.objects.get(pk=int(item))
                    contact.delete()
                except ValueError:
                    return Response({'status': False, 'error': 'Не верный тип поля'}, status=status.HTTP_400_BAD_REQUEST
                                    )
            return Response({'status': True}, status=status.HTTP_204_NO_CONTENT)
        return Response({'status': False, 'error': 'Не указаны ID контактов'}, status=status.HTTP_400_BAD_REQUEST)


class ContactAPIList(generics.ListCreateAPIView):
    """
       API представление для списка и создания контактов.
    """
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    """
        A class for updating partner information.
        Methods:
        - post: Update the partner information.
        Attributes:
        - None
    """
    """
        Этот класс используется для обновления информации о партнере.
        Метод post отвечает за обновление информации о ценниках партнера. 
        Он принимает запрос Django request и выполняет следующие действия:
        Проверяется, что тип пользователя - 'shop'. Если нет, возвращается JSON-ответ 
        со статусом False и сообщением об ошибке.
        Из данных запроса извлекается URL. Если URL есть, то продолжается обработка.
        URL проверяется с помощью URLValidator. Если URL недействителен, возвращается
        JSON-ответ со статусом False и сообщением об ошибке.
        Если URL действителен, то содержимое URL получается с помощью функции get и
        загружается в виде YAML-данных.
        Создается или получается объект Shop с данными из YAML.
        Создаются или получаются объекты Category для каждой категории в YAML и связываются 
        с объектом Shop.
        Удаляются все объекты ProductInfo, связанные с объектом Shop.
        Создаются объекты ProductInfo для каждого элемента в YAML, связываются с 
        соответствующими объектами Product и Shop.
        Создаются объекты ProductParameter для каждого параметра в YAML, связываются с
        соответствующими объектами ProductInfo и Parameter.
        Возвращается JSON-ответ со статусом True.
        Если URL не указан в данных запроса, возвращается JSON-ответ со статусом
        False и сообщением об ошибке, указывающим, что не указаны все необходимые аргументы.

        """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'change_price'

    def post(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response({'status': False, 'error': 'Только для магазинов'}, status=status.HTTP_403_FORBIDDEN)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return Response({'status': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                stream = get(url).content
                data = load_yaml(stream, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(user_id=request.user.id, defaults={
                    'name': data['shop'], 'url': url})
                if shop.name != data['shop']:
                    return Response({'status': False, 'error': 'В файле некорректное название магазина'},
                                    status=status.HTTP_400_BAD_REQUEST)
                return Response({'status': True})
        return Response({'status': False, 'error': 'Не указаны все необходимые поля'},
                        status=status.HTTP_400_BAD_REQUEST)


class PartnerState(APIView):
    """
        A class for managing partner state.
        Methods:
           - get: Retrieve the state of the partner
        Attributes:
           - None
    """
    """
        Этот класс используется для управления статусом партнера.
        В классе PartnerState определены два метода: 
        Метод [get] используется для получения статуса партнера. Он проверяет, 
        что пользователь авторизован и является магазином. Если проверки проходят успешно,
        то он сериализует объект магазина и возвращает сериализованные данные в ответе.

        Метод [post] используется для обновления статуса партнера. Он также проверяет,
        что пользователь авторизован и является магазином. Если проверки проходят успешно,
        то он получает параметр state из запроса. Если параметр state предоставлен, 
        то он обновляет статус магазина и возвращает ответ с указанием успеха операции.
        Если параметр state не предоставлен, то возвращается ответ с указанием
        необходимости указания всех необходимых аргументов.

        Таким образом, класс PartnerState предоставляет API для управления статусом партнера.
        """
    permission_classes = [IsAuthenticated]

    # получить текущий статус
    def get(self, request, *args, **kwargs):
        """Функция для получения статуса магазина"""
        if request.user.type != 'shop':
            return Response({'status': False, 'error': 'Только для магазинов'}, status=status.HTTP_403_FORBIDDEN)
        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    # изменить текущий статус
    def post(self, request, *args, **kwargs):
        """Функция изменения статуса магазина"""
        if request.user.type != 'shop':
            return Response({'status': False, 'error': 'Только для магазинов'}, status=status.HTTP_403_FORBIDDEN)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return Response({'status': True})
            except ValueError as error:
                return Response({'status': False, 'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': False, 'error': 'Не указано поле Статус'}, status=status.HTTP_400_BAD_REQUEST)


class PartnerOrders(APIView):
    """
        Класс для получения заказов поставщиками
         Methods:
        - get: Retrieve the orders associated with the authenticated partner.
        Attributes:
        - None
    """
    """
        У этого класса есть метод get, который отвечает за получение заказов, 
        связанных с авторизованным партнером.
        Затем он проверяет, является ли тип пользователя 'shop' (магазин). 
        Если нет, возвращает JSON-ответ с кодом состояния 403 и сообщением об ошибке.
        Затем он выполняет запрос к модели Order, чтобы получить заказы, 
        связанные с партнером. Он фильтрует заказы на основе поля 
        ordered_items__product_info__shop__user_id, исключает заказы с 
        состоянием 'basket' и выполняет предварительную связь с несколькими полями 
        модели Order. Затем он выбирает связанные данные и вычисляет общую сумму 
        для каждого заказа, используя функцию Sum. Затем он суммирует все суммы 
        с помощью функции Sum. Наконец, он возвращает сериализованные данные
        заказов в виде ответа.

    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Функция для получения заказов поставщиками"""
        if request.user.type != 'shop':
            return Response({'status': False, 'error': 'Только для магазинов'}, status=status.HTTP_403_FORBIDDEN)
        prefetch = Prefetch('ordered_items', queryset=OrderItem.objects.filter(
            shop__user_id=request.user.id))
        order = Order.objects.filter(
            ordered_items__shop__user_id=request.user.id).exclude(status='cart')\
            .prefetch_related(prefetch).select_related('contact').annotate(
                    total_sum=Sum('ordered_items__total_amount'),
                    total_quantity=Sum('ordered_items__quantity'))
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ShopView(generics.ListAPIView):
    """ Класс просмотра списка магазинов"""
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class CategoryView(generics.ListCreateAPIView):
    """ Класс просмотра списка категорий"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @extend_schema(request=CategorySerializer, responses={200: CategorySerializer})
    def get(self, request):
        """ Метод возвращает список категорий. """

        category_list = super().get(request)
        return category_list


class ProductView(APIView):
    """ Класс просмотра списка товаров
        Используется Django REST Framework's `APIView` для обработки HTTP-запросов.
        Также используется `ApiListPagination` для пагинации.

        Метод [get] используется для обработки GET-запросов.
    """
    pagination_class = ApiListPagination

    def get(self, request, *args, **kwargs):
        """
            Обрабатывает GET-запросы для списка продуктов.
            Args:
                request (HttpRequest): HTTP-запрос.
                *args: Список аргументов переменной длины.
                **kwargs: Произвольные именованные аргументы.
            Returns:
                Response: Сериализованные данные о продуктах.

        """
        # Строим запрос для фильтрации продуктов по магазину и категории
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')
        if shop_id:
            query = query & Q(shop_id=shop_id)
        if category_id:
            query = query & Q(category_id=category_id)
        # Запрос в базу данных для продуктов с указанными фильтрами
        queryset = Product.objects.filter(query).select_related('shop', 'category').\
            prefetch_related('product_parameters').distinct()
        # Сериализация данных о продуктах
        serializer = ProductSerializer(queryset, many=True)
        # Возврат сериализованных данных о продуктах в ответе
        return Response(serializer.data)

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
        API-конечная точка, которая позволяет просматривать товары.
    """
    # Запрос к товарам, которые будут просмотрены
    queryset = Product.objects.all()
    # Сериализатор для просмотра данных о продуктах
    serializer_class = ProductSerializer


class CartView(APIView):
    """Класс корзины покупателей
    Этот код представляет собой часть класса BasketView,
    который отвечает за управление корзиной покупателя.
    """
    """
        A class for managing the user's shopping basket.
        Methods:
        - get: Retrieve the items in the user's basket.
        - post: Add an item to the user's basket.
        - put: Update the quantity of an item in the user's basket.
        - delete: Remove an item from the user's basket.
        Attributes:
        - None
        """
    permission_classes = [IsAuthenticated]

    # получить корзину
    def get(self, request, *args, **kwargs):
        """Функция для получения содержимого корзины"""
        cart = Order.objects.filter(
            user_id=request.user.id, status='cart'
        ).prefetch_related('ordered_items').annotate(
            total_sum=Sum('ordered_items__total_amount'),
            total_quantity=Sum('ordered_items__quantity')
        )
        serializer = OrderSerializer(cart, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        '''
        Функция для добавление товаров в корзину
        '''
        items = request.data.get('items')
        if items:
            try:
                items_dict = load_json(items)
            except ValueError:
                Response({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                cart, _ = Order.objects.get_or_create(user_id=request.user.id, status='cart')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': cart.id})
                    product = Product.objects.filter(external_id=order_item['external_id']).values('category', 'shop',
                                                                                                   'name', 'price')
                    order_item.update({'category': product[0]['category'], 'shop': product[0]['shop'],
                                       'product_name': product[0]['name'], 'price': product[0]['price']})
                    serializer = OrderItemAddSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return Response({'status': False, 'errors': str(error)},
                                            status=status.HTTP_400_BAD_REQUEST)
                        else:
                            objects_created += 1
                    else:
                        return Response({'status': False, 'error': serializer.errors},
                                        status=status.HTTP_400_BAD_REQUEST)
                return Response({'status': True, 'num_objects': objects_created})

        return Response({'status': False, 'error': 'Не указаны необходимые поля'},
                        status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        """Функция для изменения количества товара в корзине"""
        """
           Метод put обрабатывает PUT-запросы и используется для обновления количества товаров
            в корзине.  Если данные корректны, он обновляет количество товаров в 
            корзине, используя OrderItem.objects.filter(order_id=basket.id, 
            id=order_item['id']).update(quantity=order_item['quantity']). 
            В конце метод возвращает JSON-ответ с информацией о статусе и количестве обновленных 
            объектов.
        """
        items = request.data.get('items')
        if items:
            try:
                items_dictionary = load_json(items)
            except ValueError:
                Response({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                cart, _ = Order.objects.get_or_create(user_id=request.user.id, status='cart')
                objects_updated = 0
                for item in items_dictionary:
                    if isinstance(item['id'], int) and isinstance(item['quantity'], int):
                        objects_updated += OrderItem.objects.filter(order_id=cart.id, id=item['id']).update(
                            quantity=item['quantity'])
                return Response({'status': True, 'edit_objects': objects_updated})
        return Response({'status': False, 'error': 'Не указаны все поля'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        """Функция для удаления товара из корзины"""
        items = request.data.get('items')
        if items:
            items_list = items.split(',')
            cart, _ = Order.objects.get_or_create(user_id=request.user.id, status='cart')
            query = Q()
            objects_deleted = False
            for item_id in items_list:
                if item_id.isdigit():
                    query = query | Q(order_id=cart.id, id=item_id)
                    objects_deleted = True
            if objects_deleted:
                count = OrderItem.objects.filter(query).delete()[0]
                return Response({'status': True, 'del_objects': count}, status=status.HTTP_204_NO_CONTENT)
        return Response({'status': False, 'error': 'Не указаны все поля'}, status=status.HTTP_400_BAD_REQUEST)


class OrderView(APIView):
    """Класс заказов покупателей"""
    """
        Класс для получения и размешения заказов пользователями
        Methods:
        - get: Retrieve the details of a specific order.
        - post: Create a new order.
        Attributes:
        - None
    """
    permission_classes = [IsAuthenticated]

    # получить мои заказы
    def get(self, request, *args, **kwargs):
        """Функция получения списка заказанных товаров """
        order = Order.objects.filter(
            user_id=request.user.id).annotate(total_quantity=Sum('ordered_items__quantity'), total_sum=Sum(
                'ordered_items__total_amount')).distinct()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):
        """Функция подтверждения заказа"""
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log is required'}, status=403)
        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                            contact_id=request.data['contact'], status='new')
                except IntegrityError as error:
                    print(error)
                    return Response({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                else:
                    if is_updated:
                        #on_change_order_status(request.user.id, request.data['id'])
                        return Response({'Status': True})
                    else:
                        error_message = 'Сбой'         
        return Response({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})
