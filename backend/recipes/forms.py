from django import forms

from recipes.models import Recipe, RecipeIngredient


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = '__all__'

    def clean_cooking_time(self):
        cooking_time = self.cleaned_data.get('cooking_time')
        if cooking_time < 1:
            raise forms.ValidationError(
                'Время готовки не может быть меньше 1'
            )
        return cooking_time


class RecipeIngredientInlineForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredient
        fields = '__all__'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount < 1:
            raise forms.ValidationError(
                'Количество ингредиента не может быть меньше 1!'
            )
        return amount


class RecipeIngredientInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if not any(
                [form.cleaned_data
                 and not form.cleaned_data.get('DELETE', False)
                 for form in self.forms]
        ):
            raise forms.ValidationError('Должен быть хотя бы 1 ингредиент!')
