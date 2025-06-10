# quiz_project/quiz_project/urls.py

from django.contrib import admin
from django.urls import path, include # <<< Thêm `include` vào

urlpatterns = [
    path('admin/', admin.site.urls),
    # Khi người dùng truy cập vào trang web gốc (''),
    # hãy chuyển tất cả các yêu cầu URL đến file urls.py của 'quiz_app'
    path('', include('quiz_app.urls')), # <<< THÊM DÒNG NÀY
]