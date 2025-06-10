from django import forms
from django.core.exceptions import ValidationError
import os

from .models import Books


def validate_file_type(file):
    """验证文件类型，只允许 PDF 和 EPUB 文件"""
    # 支持的文件扩展名
    allowed_extensions = ['.pdf', '.epub']
    
    # 获取文件扩展名
    file_extension = os.path.splitext(file.name)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f'不支持的文件类型：{file_extension}。只支持 PDF 和 EPUB 文件。'
        )
    
    # 检查文件 MIME 类型（额外安全检查）
    allowed_mime_types = [
        'application/pdf',
        'application/epub+zip',
        'application/x-epub+zip',
        'application/octet-stream'  # 某些浏览器可能将 epub 识别为这个类型
    ]
    
    if hasattr(file, 'content_type') and file.content_type:
        if file.content_type not in allowed_mime_types:
            raise ValidationError(
                f'不支持的文件格式。只支持 PDF 和 EPUB 文件。'
            )


class UploadFileForm(forms.ModelForm):
    file = forms.FileField(
        label='选择文件',
        help_text='只支持 PDF 和 EPUB 格式的电子书文件',
        validators=[validate_file_type],
        widget=forms.FileInput(attrs={
            'class': 'file-input file-input-bordered file-input-primary w-full max-w-xs',
            'accept': '.pdf,.epub'
        })
    )
    
    class Meta:
        model = Books
        fields = ("file",)
        
    def clean_file(self):
        """额外的文件验证"""
        file = self.cleaned_data.get('file')
        
        if file:
            # 检查文件大小（可选，根据需要调整）
            max_size = 100 * 1024 * 1024  # 100MB
            if file.size > max_size:
                raise ValidationError(f'文件太大，最大支持 {max_size // (1024*1024)}MB')
                
        return file
