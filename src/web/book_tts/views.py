from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.conf import settings
from .forms import TurnstileAuthenticationForm, TurnstileUserCreationForm


class TurnstileLoginView(LoginView):
    """带有 Turnstile 验证的登录视图"""
    form_class = TurnstileAuthenticationForm
    template_name = 'registration/login.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 只在非 debug 模式下添加 Turnstile
        if not settings.DEBUG:
            context['turnstile_site_key'] = settings.TURNSTILE_SITE_KEY
        return context


class TurnstileRegisterView(CreateView):
    """带有 Turnstile 验证的注册视图"""
    form_class = TurnstileUserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 只在非 debug 模式下添加 Turnstile
        if not settings.DEBUG:
            context['turnstile_site_key'] = settings.TURNSTILE_SITE_KEY
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 注册成功后自动登录用户
        login(self.request, self.object)
        return redirect('home')  # 重定向到首页 