
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Store, CartItem, DispensingLog, Sales, Customers, Wallet
from .forms import addToStoreForm, searchForm, salesForm, AddFundsForm, RegistrationForm, CustomerForm
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import F, Sum, ExpressionWrapper, fields
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.functions import TruncDay, TruncMonth





# Create your views here.
def index(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('index')
    else:
        return render(request, 'app/index.html')



def logout_user(request):
    logout(request)
    return redirect('index')



def home(request):
    return render(request, 'app/home.html', {})


def is_admin(user):
    return user.is_authenticated and user.is_superuser

def store(request):
    if request.user.is_authenticated:
        store_items = Store.objects.all()
        total_stock_value = calculate_stock_value(request)
        return render(request, 'app/store.html', {
            'store_items': store_items, 
            'total_stock_value': total_stock_value
            })
    else:
        return render(request, 'app/index.html',{})
    
    
def calculate_stock_value(request):
    total_stock_value = Store.objects.annotate(
        total_value = ExpressionWrapper(F('selling_price') * F('stock_quantity'), output_field=fields.DecimalField())
    ).aggregate(Sum('total_value'))['total_value__sum']
    return total_stock_value or 0

@user_passes_test(is_admin)
@transaction.atomic
def add_item(request):
    form = addToStoreForm(request.POST or None)
    if request.user.is_authenticated:
        if request.method == 'POST':
            if form.is_valid():
                form.save()
                messages.success(request, 'Item saved successfully.')
                return redirect('store')
        return render(request, 'app/add_item.html', {'form': form})
    else:
        return render(request, 'app/index.html', {})
    

@user_passes_test(is_admin)
def edit_item(request, pk):
    if request.user.is_authenticated:
        edit_item = Store.objects.get(id=pk)
        form = addToStoreForm(request.POST or None, instance=edit_item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item successfully updated.')
            return redirect('store')
        return render(request, 'app/edit_item.html', {'form': form})
    else:
        return render(request, 'app/index.html')
    
    
def search_item(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = searchForm(request.POST)
            if form.is_valid():
                search_query = form.cleaned_data['search_query']
                results = Store.objects.filter(name__icontains=search_query)
            else:
                results = None
        else:
            form = searchForm()
            results = None
    return render(request, 'app/search_item.html', {'form': form, 'results': results})


@transaction.atomic
def add_to_cart(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Store, id=pk)
        if request.method == 'POST':
            quantity = int(request.POST['quantity'])
            # customer = Customers.objects.get(user=request.user)
            # wallet, created = wallet.objects.get_or_create(customer=customer)
            total_price = item.selling_price * quantity
            
            # if wallet.balance >= total_price:
            #     wallet.balance -= total_price
            #     wallet.save()
                
                # item.stock_quantity -= quantity
                # item.save()
                # CartItem.objects.get_or_create(item=item, quantity=quantity)
                # return redirect('view_cart')
            if item.stock_quantity >= quantity:
                cart_item, created = CartItem.objects.get_or_create(item=item, defaults={'quantity': 0})
                
                if created:
                    cart_item.quantity = quantity
                else:
                    cart_item.quantity += quantity
                
                if item.stock_quantity >= cart_item.quantity:
                    item.stock_quantity -= quantity
                    item.save()
                    # DispensingLog.objects.create(user=request.user, name=item.name, quantity=quantity)
                    cart_item.save()
                    
                    return redirect('view_cart')
                else:
                    messages.error(request, f"Sorry, the total requested quantity ({cart_item.quantity}) exceeds the available stock quantity ({item.stock_quantity}).")
            else:
                messages.error(request, f"Sorry, the requested quantity ({quantity}) exceeds the available stock quantity ({item.stock_quantity}).")

        return render(request, 'app/add_to_cart.html', {'item': item})
    return render(request, 'app/index.html', {})   




def view_cart(request):
    cart_items = CartItem.objects.all()
    
    total_price = 0
    total_discount = 0
    total_discounted_price = 0
    for cart_item in cart_items:
        cart_item.subtotal = cart_item.item.selling_price * cart_item.quantity
        cart_item.discounted_subtotal = cart_item.subtotal - cart_item.discount_amount
        total_price += cart_item.subtotal
        total_discount += cart_item.discount_amount
        total_discounted_price = total_price - total_discount
        
    return render(request, 'app/view_cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_discounted_price': total_discounted_price,
        })

def update_cart_item_quantity(request, pk):
    cart_item = get_object_or_404(CartItem, id=pk)
    item = cart_item.item

    if request.method == 'POST':
        quantity_to_return_str = request.POST.get('quantity', '').strip()

        # Check if the quantity to return is empty
        if not quantity_to_return_str:
            return redirect('error_page')

        try:
            quantity_to_return = int(quantity_to_return_str)
        except ValueError:
            return redirect('error_page')

        if 0 < quantity_to_return <= cart_item.quantity:
            # Update stock quantity
            item.stock_quantity += quantity_to_return
            item.save()
            
            # Update cart item quantity
            cart_item.quantity -= quantity_to_return
            cart_item.save()
            
            # If cart item quantity becomes 0, delete it
            if cart_item.quantity == 0:
                cart_item.delete()
                
            return redirect('view_cart')
        else:
            return redirect('error_page')

    return render(request, 'app/view_cart.html', {'cart_item': cart_item})


def discount(request, pk):
    cart_items = CartItem.objects.filter(id=pk)  
    total_price = sum(item.item.selling_price * item.quantity for item in cart_items)
    total_discount = 0  # Initialize total discount

    if request.method == 'POST':
        for cart_item in cart_items:
            discount_amount = request.POST.get(f'discount_amount-{cart_item.id}')
            if discount_amount:
                discount_amount = float(discount_amount)
                cart_item.discount_amount = discount_amount
                cart_item.save()
                total_discount += discount_amount  # Accumulate the discount amount

        return redirect('view_cart')

    total_discounted_price = total_price - total_discount  # Calculate the total discounted price

    return render(request, 'app/view_cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_discounted_price': total_discounted_price,
    })


def error_page(request):
    return render(request, 'app/error_page.html')


def clear_cart(request):
    if request.method == "POST":
        cart_items = CartItem.objects.filter()
        for cart_item in cart_items:
            store_item = Store.objects.get(id=cart_item.item.id)
            store_item.stock_quantity += cart_item.quantity
            store_item.save()
            cart_item.delete()
        messages.success(request, 'Cart cleared and item(s) returned to store.')
        return redirect('view_cart')
    

def receipt(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.all()
    
        total_price = 0
        total_discount = 0
        total_discounted_price = 0
        for cart_item in cart_items:
            cart_item.subtotal = cart_item.item.selling_price * cart_item.quantity
            cart_item.discounted_subtotal = cart_item.subtotal - cart_item.discount_amount
            total_price += cart_item.subtotal
            total_discount += cart_item.discount_amount
            total_discounted_price = total_price - total_discount
            
            # Determine if the sale is on credit based on wallet balance
            # customer = Customers.objects.get(user=request.user)
            # wallet = Wallet.objects.get(customer=customer)
            # on_credit = wallet.balance < total_discounted_price

            # Deduct from wallet balance if sufficient
            # if not on_credit:
            #     wallet.balance -= total_discounted_price
        
            # Create a sales entry for each item in the cart
            Sales.objects.create(
                user=request.user,
                name=cart_item.item.name,
                quantity=cart_item.quantity,
                amount=cart_item.discounted_subtotal,
                # on_credit=on_credit
            )
        
        # Add each item to the DispensingLog after generating the sales receipt
        for cart_item in cart_items:
            DispensingLog.objects.create(
                user=request.user,
                name=cart_item.item.name,
                quantity=cart_item.quantity
            )
        
        # Clear the cart after generating the receipt and logging the dispensing
        CartItem.objects.all().delete()
        
        return render(request, 'app/receipt.html', {
            'date': timezone.now(),
            'cart_items': cart_items,
            'total_price': total_price,
            'total_discounted_price': total_discounted_price,
        })
    return render(request, 'app/index.html', {})


@user_passes_test(is_admin)
def dispensing_log(request):
    logs = DispensingLog.objects.all().order_by('-created_at')
    
    # Check if a date is provided in the request
    if request.GET.get('date'):
        selected_date = parse_date(request.GET.get('date'))
        if selected_date:
            logs = logs.filter(created_at__date=selected_date)
    
    return render(request, 'app/dispensing-log.html', {'logs': logs})
def get_daily_sales():
    daily_sales = Sales.objects.annotate(
        day=TruncDay('date')
    ).values('day').annotate(
        total_sales=Sum('amount')
    ).order_by('day')
    return daily_sales

def get_monthly_sales():
    monthly_sales = Sales.objects.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_sales=Sum('amount')
    ).order_by('month')
    return monthly_sales

@user_passes_test(is_admin)
def daily_sales(request):
    daily_sales = get_daily_sales().order_by('-day')
    return render(request, 'app/daily_sales.html', {'daily_sales': daily_sales})

@user_passes_test(is_admin)
def monthly_sales(request):
    monthly_sales = get_monthly_sales().order_by('-month')
    return render(request, 'app/monthly_sales.html', {'monthly_sales': monthly_sales})



def search_sales(request):
    if request.method == 'POST':
        form = salesForm(request.POST)
        if form.is_valid():
            search_date = form.cleaned_data['search_date']
            daily_sales = Sales.objects.filter(date=search_date).aggregate(total_sales=Sum('amount'))['total_sales'] or 0
            monthly_sales = Sales.objects.filter(date__month=search_date.month, date__year=search_date.year).aggregate(total_sales=Sum('amount'))['total_sales'] or 0
            
            return render(request, 'app/search_sales.html', {
                'search_date': search_date,
                'daily_sales': daily_sales,
                'monthly_sales': monthly_sales,
            })
    else:
        form = salesForm()
    return render(request, 'app/search_sales.html', {'form': form})


def exp_date_alert(request):
    if request.user.is_authenticated:
        # Define the alert threshold (e.g., 90 days before expiration)
        alert_threshold = timezone.now() + timedelta(days=90)
        
        # Get items that are expiring within the next 90 days
        expiring_items = Store.objects.filter(expiry_date__lte=alert_threshold, expiry_date__gt=timezone.now())
        
        # Get items that have already expired
        expired_items = Store.objects.filter(expiry_date__lt=timezone.now())
        
        # Zero the quantity of expired items
        for expired_item in expired_items:
            if expired_item.stock_quantity > 0:
                # Optionally, log the removal for auditing purposes
                DispensingLog.objects.create(
                    user=request.user,
                    name=expired_item.name,
                    quantity=expired_item.stock_quantity,
                )
                # Set stock quantity to zero
                expired_item.stock_quantity = 0
                expired_item.save()
        
        return render(request, 'app/exp_date_alert.html', {
            'expiring_items': expiring_items,
            'expired_items': expired_items,
        })
    else:
        return redirect('index')

    
@user_passes_test(is_admin)
def add_new_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2'] 
        
        if password == password2:
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username already in use')
                return redirect('add_new_user')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()
                return redirect('index')
        else:
            return render (request, 'app/add_new_user.html', {})
    return render(request, 'app/add_new_user.html', {})





def add_customer(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer added successfully!') 
            return redirect('customer_list')  # Redirect to the customer list after saving
    else:
        form = CustomerForm()
    return render(request, 'app/add_customer.html', {'form': form})




def customer_list(request):
    customers = Customers.objects.all()
    return render(request, 'app/customer_list.html', {'customers': customers})


@login_required
@user_passes_test(is_admin)
def delete_customer(request, pk):
    customer = get_object_or_404(Customers, pk=pk)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted successfully.')
        return redirect('customer_list')
    return render(request, 'app/delete_customer.html', {'customer': customer})





@user_passes_test(is_admin)
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Registration successful, but login failed. Please try logging in manually.')
                return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()
    return render(request, 'app/register.html', {'form': form})



@login_required
@transaction.atomic
def add_funds(request, customer_id):
    customer = get_object_or_404(Customers, id=customer_id)
    wallet = customer.wallet

    if request.method == 'POST':
        form = AddFundsForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            wallet.add_funds(amount)
            messages.success(request, 'Funds added successfully.')
            return redirect('wallet_details', customer_id=customer_id)
    else:
        form = AddFundsForm()

    return render(request, 'app/add_funds.html', {'form': form, 'customer': customer})


    
    
    
@login_required
def wallet_detail(request, customer_id):
    customer = get_object_or_404(Customers, id=customer_id)
    wallet = customer.wallet
    return render(request, 'app/wallet_detail.html', {'wallet': wallet, 'customer': customer})


    
    
    
@login_required
@transaction.atomic
def purchase_items(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        customer = get_object_or_404(Customers, id=customer_id)
        wallet = customer.wallet
        
        item_ids = request.POST.getlist('item_ids')
        total_price = 0
        items_with_quantities = []
        insufficient_stock = False
        
        for item_id in item_ids:
            item = get_object_or_404(Store, id=item_id)
            quantity = int(request.POST.get(f'quantity_{item_id}', 1))
            
            if item.stock_quantity < quantity:
                messages.error(request, f'Insufficient stock for {item.name}. Available: {item.stock_quantity}')
                insufficient_stock = True
            else:
                total_price += item.selling_price * quantity
                items_with_quantities.append((item, quantity))

        if insufficient_stock:
            return redirect('purchase_items')
        
        # Allow the wallet balance to go negative if needed
        wallet.balance -= total_price
        wallet.save()

        on_credit = wallet.balance < 0

        # Deduct the quantity from store and create sales records
        for item, quantity in items_with_quantities:
            item.stock_quantity -= quantity
            item.save()

            # Log the sale with customer details
            Sales.objects.create(
                user=request.user,
                customer=customer,  # Save the customer information
                name=item.name,
                quantity=quantity,
                amount=item.selling_price * quantity,
                on_credit=on_credit
            )

            # Record into DispensingLog
            DispensingLog.objects.create(
                user=request.user,
                name=item.name,
                quantity=quantity
            )

        if on_credit:
            messages.error(request, 'Items purchased on credit due to insufficient wallet balance.')
        else:
            messages.success(request, 'Items purchased successfully and wallet balance updated.')

        return redirect('wallet_details', customer_id=customer_id)
    else:
        items = Store.objects.all()
        customers = Customers.objects.all()
        return render(request, 'app/customer_purchase.html', {'items': items, 'customers': customers})



@login_required
@user_passes_test(is_admin)
def customers_on_credit(request):
    sales_on_credit = Sales.objects.filter(
        on_credit=True, 
        customer__wallet__balance__lt=0,
        # settled=False  # Assuming there is a 'settled' field indicating if the credit is paid off
    ).select_related('customer').order_by('-date')

    # Get the date filter from the request
    search_date = request.GET.get('date')
    if search_date:
        sales_on_credit = sales_on_credit.filter(date=search_date)

    customers_negative_balances = [
        {
            'customer': sale.customer,
            'balance': sale.customer.wallet.balance,
            'date': sale.date,
            'amount': sale.amount,
        }
        for sale in sales_on_credit
    ]

    return render(request, 'app/customers_on_credit.html', {
        'customers_negative_balances': customers_negative_balances,
        'search_date': search_date,
    })





@login_required
def wallet_details(request, customer_id):
    customer = get_object_or_404(Customers, id=customer_id)
    wallet = customer.wallet
    return render(request, 'app/wallet_details.html', {'wallet': wallet, 'customer': customer})



@login_required
@user_passes_test(is_admin)
def clear_balance(request, customer_id):
    wallet = get_object_or_404(Wallet, customer_id=customer_id)
    wallet.balance = 0
    wallet.save()
    messages.success(request, 'Wallet balance has been cleared.')
    return redirect('wallet_details', customer_id=customer_id)


@login_required
@user_passes_test(is_admin)
def delete_customer(request, pk):
    customer = get_object_or_404(Customers, pk=pk)
    customer.delete()
    messages.success(request, 'Customer deleted successfully.')
    return redirect('customer_list')  #
    