from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .turnstile import verify_turnstile, get_client_ip


class TurnstileAuthenticationForm(AuthenticationForm):
    """带有 Turnstile 验证的登录表单"""
    
    cf_turnstile_response = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.request = request
        
        # 自定义字段属性
        self.fields['username'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': '输入用户名'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': '输入密码'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 验证 Turnstile
        turnstile_token = cleaned_data.get('cf_turnstile_response')
        if turnstile_token and self.request:
            client_ip = get_client_ip(self.request)
            verification_result = verify_turnstile(turnstile_token, client_ip)
            
            if not verification_result['success']:
                raise forms.ValidationError("人机验证失败，请重试")
        
        return cleaned_data


class TurnstileUserCreationForm(UserCreationForm):
    """带有 Turnstile 验证的注册表单"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': '输入邮箱'
        })
    )
    
    cf_turnstile_response = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        
        # 自定义字段属性
        self.fields['username'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': '输入用户名'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': '输入密码'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': '再次输入密码'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 验证 Turnstile
        turnstile_token = cleaned_data.get('cf_turnstile_response')
        if turnstile_token and self.request:
            client_ip = get_client_ip(self.request)
            verification_result = verify_turnstile(turnstile_token, client_ip)
            
            if not verification_result['success']:
                raise forms.ValidationError("人机验证失败，请重试")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user 