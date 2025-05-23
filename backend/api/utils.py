import csv
import os
from datetime import datetime
from io import BytesIO

from django.db.models import Sum
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from meals.models import RecipeIngredient

# def generate_shopping_list(user):
#     """."""
#     # Получаем агрегированные данные из БД
#     ingredients = RecipeIngredient.objects.filter(
#         recipe__shopping_carts__user=user
#     ).values(
#         'ingredient__name',
#         'ingredient__unit'
#     ).annotate(total_amount=Sum('amount'))

#     # Группируем ингредиенты
#     grouped = defaultdict(list)
#     for item in ingredients:
#         key = f'{item["ingredient__name"]}'
#         f'({item["ingredient__unit"]})'
#         grouped[key].append(item['total_amount'])

#     # Формируем текст
#     text = "Список покупок:\n\n"
#     for name_unit, amounts in grouped.items():
#         total = sum(amounts)
#         text += f"- {name_unit}: {total}\n"

#     return text.strip()


# def generate_pdf_response(content):
#     """."""
#     buffer = BytesIO()
#     p = canvas.Canvas(buffer)
#     text = p.beginText(40, 800)
#     for line in content.split('\n'):
#         text.textLine(line)
#     p.drawText(text)
#     p.showPage()
#     p.save()
#     buffer.seek(0)
#     response = HttpResponse(buffer, content_type='application/pdf')
#     response['Content-Disposition'] = (
#         'attachment; filename="shopping_list.pdf"'
#     )
#     return response


def generate_shopping_list(user):
    """
    Генерирует список покупок для указанного пользователя.

    Собирает все ингредиенты из рецептов, добавленных в корзину пользователя,
    и суммирует их количество.
    """
    ingredients = RecipeIngredient.objects.filter(
        recipe__shopping_carts__user=user
    ).values(
        'ingredient__name',
        'ingredient__measurement_unit'
    ).annotate(total_amount=Sum('amount'))
    return {
        'ingredients': [
            {
                'name': item['ingredient__name'],
                'unit': item['ingredient__measurement_unit'],
                'amount': item['total_amount']
            }
            for item in ingredients
        ],
        'total': ingredients.count()
    }


def generate_shopping_list_text(content):
    """Форматирует список покупок в читаемый текстовый формат."""
    text = "Список покупок:\n\n"    """."""
    for item in content['ingredients']:
        text += f"- {item['name']} ({item['unit']}): {item['amount']}\n"
    return text.strip()


def generate_pdf_response(content, user):
    """
    Генерирует PDF-документ со списком покупок.

    Создает структурированный PDF-документ с логотипом, информацией о
    пользователе и таблицей ингредиентов. Поддерживает русскоязычное
    отображение текста.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=1,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    elements = []
    logo_path = 'static/logo.png'
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=4 * cm, height=4 * cm)
        elements.append(logo)
    title = Paragraph("Список покупок Foodgram", title_style)
    elements.append(title)
    user_info = [
        ['Пользователь:', user.get_full_name() or user.username],
        ['Дата генерации:', datetime.now().strftime('%d.%m.%Y %H:%M')]
    ]
    user_table = Table(user_info, colWidths=[4 * cm, 10 * cm])
    user_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 12),
        ('FONTSIZE', (1, 0), (1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(user_table)
    elements.append(Spacer(1, 1 * cm))
    data = [['Ингредиент', 'Количество']]
    for item in content['ingredients']:
        data.append([
            Paragraph(f"{item['name']} ({item['unit']})", styles['BodyText']),
            f"{item['amount']}"
        ])
    ingredients_table = Table(
        data,
        colWidths=[12 * cm, 4 * cm],
        repeatRows=1
    )
    ingredients_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(ingredients_table)
    footer = Paragraph(
        f"Всего ингредиентов: {len(content['ingredients'])}",
        ParagraphStyle(
            'Footer',
            parent=styles['BodyText'],
            fontSize=12,
            alignment=2,
            spaceBefore=20
        )
    )
    elements.append(footer)
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="foodgram_shopping_list.pdf"'
    )
    return response


def generate_csv_response(content):
    """Генерирует CSV-файл со списком покупок."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        'attachment; filename="shopping_list.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(['Ингредиент', 'Количество'])
    for item in content['ingredients']:
        writer.writerow([f"{item['name']} ({item['unit']})", item['amount']])
    return response


def generate_txt_response(content):
    """Генерирует текстовый файл со списком покупок."""
    text = generate_shopping_list_text(content)
    response = HttpResponse(text, content_type='text/plain')
    response['Content-Disposition'] = (
        'attachment; filename="shopping_list.txt"'
    )
    return response
