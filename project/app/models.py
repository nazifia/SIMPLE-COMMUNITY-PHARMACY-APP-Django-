from django.db import models

# Create your models here.
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Store(models.Model):
    name = models.CharField(max_length=100)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField()
    expiry_date = models.DateField()
    
    def __str__(self):
        return (f"{self.name} ({self.purchase_price}) ({self.selling_price}) ({self.stock_quantity}) ({self.expiry_date})")
    


class CartItem(models.Model):
    item = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.IntegerField(null=True, default=1)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    


class DispensingLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} {self.name} {self.quantity} {self.created_at}"



class Customers(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.name} {self.phone} {self.address}"



class Sales(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    customer = models.ForeignKey(Customers, on_delete=models.SET_NULL, null=True)  # Add this line
    name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    on_credit = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} {self.name} {self.quantity} {self.amount}"



class Wallet(models.Model):
    customer = models.OneToOneField(Customers, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.customer.name}'s Wallet - Balance: {self.balance}"
    
    
    def add_funds(self, amount):
        self.balance += amount
        self.save()
        
        
    def clear_balance(self):
        self.balance = 0
        self.save()



    
@receiver(post_save, sender=Customers)
def create_customer_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(customer=instance)




