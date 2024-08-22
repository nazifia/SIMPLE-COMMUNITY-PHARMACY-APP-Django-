from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Store, Customers

class addToStoreForm(forms.ModelForm):
    name = forms.CharField(max_length=100, label="", required=True, widget=forms.TextInput(attrs={'placeholder':'ENTER ITEM NAME', 'class':'form-control'}))
    purchase_price = forms.IntegerField()
    selling_price = forms.IntegerField()
    stock_quantity = forms.IntegerField()
    expiry_date = forms.DateField(label="", widget=forms.DateInput(attrs={'type': 'date', 'class':'form-control'}))
    
    class Meta:
        model = Store
        fields = ['name', 'purchase_price', 'selling_price', 'stock_quantity', 'expiry_date']
        
    
class searchForm(forms.Form):
    search_query = forms.CharField(min_length=2, label="", required=True, widget=forms.TextInput(attrs={'placeholder': 'SEARCH ITEM HERE'}))
    

class DiscountForm(forms.Form):
    discount_amount = forms.DecimalField(max_digits=10, decimal_places=2)
    

class salesForm(forms.Form):
    search_date = forms.DateField(label='Search Date', widget=forms.TextInput(attrs={'type': 'date'}))
    
    

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customers
        fields = ['name', 'phone', 'address']



    
class DiscountForm(forms.Form):
    discount_amount = forms.DecimalField(max_digits=10, decimal_places=2, label='Discount Amount')
    
    

class RegistrationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super(RegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class AddFundsForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2)
    
    
