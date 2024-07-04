from django.db import models

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator


USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

STATE_CHOICES = (
    ('cart', 'В корзине'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

# Create your models here.

class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """

    use_in_migrations = True
    """
	Этот метод создает и сохраняет пользователя с заданным электронным адресом,
	паролем и дополнительными полями. Он проверяет, что электронный адрес предоставлен,
	 нормализует его,создает объект пользователя с заданными полями, устанавливает пароль, 
	сохраняет пользователя в базе данных и возвращает созданного пользователя.
    """


    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        Создайте и сохраните пользователя с указанным именем пользователя,
        адресом электронной почты и паролем.
        """
        if not email:
            raise ValueError('Email address must be set')
        if not password:
            raise ValueError('Password must be provided')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        """
		Этот метод является оболочкой для метода _create_user,
		Он устанавливает значения по умолчанию для полей is_staff и is_superuser в False,
		а затем вызывает метод [_create_user]
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)


    def create_superuser(self, email, password, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Стандартная модель пользователей
    """
    """
    Этот код определяет модель пользователя User, 
    которая расширяет стандартную модель AbstractUser в Django.

   Вот ключевые моменты:

   Класс User является подклассом AbstractUser.
   Атрибут REQUIRED_FIELDS установлен как пустой список, что означает,
    что для регистрации пользователя не требуются дополнительные поля.
   Атрибут objects установлен как экземпляр класса UserManager,
    который предоставляет дополнительные методы для управления пользователями.
   Атрибут USERNAME_FIELD установлен как 'email', что означает, 
   что адрес электронной почты используется в качестве имени пользователя
    для аутентификации.
   В целом, этот код определяет пользовательскую модель User
   с дополнительными полями и проверками для адреса электронной почты,
   компании, должности, имени пользователя и типа пользователя.
       """

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    username = None
    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)
    is_active = models.BooleanField(
         ('active'), default=False, help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'),)
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')

    def __str__(self):
        """
		Строковое представление объект: return: email
		"""
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)


class Contact(models.Model):

    """
	    Это определение модели Django для класса Contact. Он имеет следующие поля:
	    city: символьное поле с максимальной длиной в 50 символа.
	    street: символьное поле с максимальной длиной в 100 символа.
	    house: символьное поле с максимальной длиной в 15 символов.
	    structure: символьное поле с максимальной длиной в 15 символов.
	    building: символьное поле с максимальной длиной в 15 символов.
	    apartment: символьное поле с максимальной длиной в 15 символов.
	    phone: символьное поле с максимальной длиной в 20 символов.
	    Класс Meta используется для определения метаданных для модели.
	    Он устанавливает понятные имена для модели и ее множественного вида.

   """
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='contacts', blank=True, on_delete=models.CASCADE)
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом', blank=True)
    structure = models.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=15, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = "Список контактов пользователя"

    def __str__(self):
        return f'{self.city}, ул.{self.street}, дом {self.house} ({self.phone})'


class ConfirmEmailToken(models.Model):
    """
	    Этот код представляет класс модели Django под названием [ConfirmEmailToken],
	     который используется для хранения токенов подтверждения email.
	     Вот краткое описание его структуры:
	     created_at: DateTimeField, определяющий время создания токена.
	     key: CharField, представляющий сам токен.
	     В классе есть статический метод generate_key(),
	     который генерирует псевдослучайный код с использованием os.urandom
	     и binascii.hexlify. Метод save() гарантирует, что поле key установлено,
	      если оно еще не установлено. Метод __str__() возвращает строковое представление
	       токена.

	     Метакласс Meta внутри класса ConfirmEmailToken используется для установки
	     понятных имен для модели и ее множественной формы.

	"""
    user = models.ForeignKey(User, related_name='confirm_email_tokens', on_delete=models.CASCADE,
		verbose_name="The User which is associated to this password reset token")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="When was this token generated")
    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)

    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return f"Токен подтверждения Email для пользователя {self.user}"


class Shop(models.Model):
	"""
	    Модель магазина
	"""
	# Название магазина
	name = models.CharField(max_length=50, verbose_name='Название')
	# Ссылка на магазин
	url = models.URLField(verbose_name='Ссылка на файл прайса', null=True, blank=True)
	# Пользователь, связанный с магазином
	user = models.OneToOneField(User, verbose_name='Пользователь', blank=True, null=True, on_delete=models.CASCADE)
	# Статус получения заказов
	state = models.BooleanField(verbose_name='Cтатус получения заказов', default=True)

	class Meta:
		verbose_name = 'Магазин'
		verbose_name_plural = "Список магазинов"
		ordering = ('-name',)

	def __str__(self):
		"""
		Строковое представление объекта
		Shop:return: название магазина
		"""
		return self.name


class Category(models.Model):
	"""
	Модель Category также имеет вложенный класс Meta,
	который указывает verbose names для модели и ее множественного имени,
	и устанавливает сортировку экземпляров модели в порядке,
	отсортированном по полю name в обратном алфавитном порядке.
	"""
	name = models.CharField(max_length=40, verbose_name='Название')
	shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

	class Meta:
		verbose_name = 'Категория'
		verbose_name_plural = "Список категорий"
		ordering = ('-name',)

	def __str__(self):
		return self.name


class Product(models.Model):
	"""
	Этот код определяет модель Product в Django. Она имеет два поля: name и category.
	Поле name является символьным полем с максимальной длиной 80 символов, а поле category
	 является внешним ключом к модели Category. Поле category является необязательным
	 и может быть пустым. Аргумент on_delete указывает, что должно произойти, если
	 связанный объект Category будет удален.

	Класс Meta используется для указания метаданных о модели. В нем устанавливаются
	 verbose_name и verbose_name_plural, чтобы предоставить понятные для человека
	 имена для модели и ее экземпляров. Также устанавливается ordering, чтобы указать
	 порядок сортировки экземпляров по умолчанию. В данном случае экземпляры сортируются
	  по полю name в порядке убывания.

	В целом, этот код определяет модель для продукта в приложении Django,
	с полем имени и категорией.
    """
	name = models.CharField(max_length=80, verbose_name='Название')
	category = models.ForeignKey(Category, verbose_name='Категория', related_name='products', blank=True,
		on_delete=models.CASCADE)
	model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
	external_id = models.PositiveIntegerField(verbose_name='Внешний ИД')
	shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='products_info', blank=True,
		on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(verbose_name='Количество')
	price = models.PositiveIntegerField(verbose_name='Цена')
	price_rrc = models.PositiveIntegerField(verbose_name='Рекомендуемая розничная цена')

	class Meta:
		verbose_name = 'Продукт'
		verbose_name_plural = "Список продуктов"
		ordering = ('category', '-name')
		constraints = [models.UniqueConstraint(fields=['shop', 'category', 'external_id'], name='unique_product_info'), ]

	def __str__(self):
		return self.name


class Parameter(models.Model):
	"""
	Этот код определяет класс модели Django с названием Parameter.
	У модели есть поле name типа CharField с максимальной длиной в 40 символов.
	Атрибут verbose_name указывает человекопонятное имя поля,
	а атрибут verbose_name_plural указывает множественную форму имени.
	Атрибут ordering указывает на то, как должны быть отсортированы экземпляры
	модели по полю name в порядке убывания. Атрибут objects является
	пляром models.manager.Manager(), который предоставляет методы для
	взаимодействия с таблицей базы данных модели.
    """

	name = models.CharField(max_length=40, verbose_name='Название')

	class Meta:
		verbose_name = 'Имя параметра'
		verbose_name_plural = "Список имен параметров"
		ordering = ('-name',)

	def __str__(self):
		return self.name


class ProductParameter(models.Model):
	"""
    Это определение модели Django для класса ProductParameter. Он имеет три поля:

    product: внешний ключ к модели ProductInfo, с связанным именем product_parameters.
    Это позволяет установить отношение "многие к одному" между ProductParameter и
    ProductInfo.
    parameter: внешний ключ к модели Parameter, с связанным именем product_parameters.
    Это позволяет установить отношение "многие к одному" между ProductParameter
    и Parameter.
    value: символьное поле с максимальной длиной в 100 символов.
    Класс Meta используется для определения метаданных для модели.
    Он устанавливает понятные имена для модели и ее множественного вида, а также
    определяет уникальное ограничение на поля product и parameter.
    """
	product = models.ForeignKey(Product, verbose_name='Информация о продукте',
		related_name='product_parameters', blank=True, on_delete=models.CASCADE)
	parameter = models.ForeignKey(Parameter, verbose_name='Параметр',
	 	related_name='parameter', blank=True, on_delete=models.CASCADE)
	value = models.CharField(verbose_name='Значение', max_length=100)

	class Meta:
		verbose_name = 'Параметр'
		verbose_name_plural = "Список параметров"
		constraints = [models.UniqueConstraint(fields=['product', 'parameter'], name='unique_product_parameter'), ]

	def __str__(self):
		return f'{self.product} - {self.parameter} {self.value}'


class Order(models.Model):
	"""
	Этот код определяет класс модели Order с полями, такими как user, created, updated,
	status и contact. Он представляет собой заказ в системе и включает метаданные,
	такие как verbose_name и ordering. Метод __str__ возвращает строковое
	представление даты и времени заказа.
	"""
	user = models.ForeignKey(User, verbose_name='Пользователь', related_name='shopAPI', blank=True,
		on_delete=models.CASCADE)
	status = models.CharField(verbose_name='Статус', choices=STATE_CHOICES, max_length=15, default='cart')
	contact = models.ForeignKey(Contact, verbose_name='Контакт', blank=True, null=True,
		on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Заказ'
		verbose_name_plural = "Список заказов"
		ordering = ('-created',)

	def __str__(self):
		return str(self.created)
		# return self.created


class OrderItem(models.Model):
	"""
	Модель заказанного товара.
    Атрибуты:
	order (ForeignKey): Заказ, к которому относится этот товар.
	product_info (ForeignKey): Информация о продукте.
	quantity (PositiveIntegerField): Количество товара.
	"""
	order = models.ForeignKey(Order, verbose_name='Заказ', related_name='ordered_items', blank=True,
		on_delete=models.CASCADE)
	category = models.ForeignKey(Category, verbose_name='Категория товара', blank=True, null=True,
		on_delete=models.SET_NULL)
	shop = models.ForeignKey(Shop, verbose_name='магазин', blank=True, null=True, on_delete=models.SET_NULL)
	product_name = models.CharField(max_length=80, verbose_name='Название товара')
	external_id = models.PositiveIntegerField(verbose_name='Внешний ИД')
	quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
	price = models.PositiveIntegerField(default=0, verbose_name='Цена')
	total_amount = models.PositiveIntegerField(default=0, verbose_name='Общая стоимость')

	class Meta:
		"""
	    Метаданные для модели OrderItem.
        Атрибуты:
	    verbose_name (str): Понятное имя модели.
		verbose_name_plural (str): Понятное имя модели в множественном числе.
		constraints (list): Список ограничений для модели.
		"""
		verbose_name = 'Заказанная позиция'
		verbose_name_plural = "Список заказанных позиций"
		constraints = [
			models.UniqueConstraint(fields=['order_id', 'product_name'], name='unique_order_item'), ]

	def __str__(self):
		return self.product_name

	def save(self, *args, **kwargs):
		self.total_amount = self.price * self.quantity
		super(OrderItem, self).save(*args, **kwargs)
