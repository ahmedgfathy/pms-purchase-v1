from django import template

from .. import services
from accounts.translations import tr

register = template.Library()


@register.simple_tag
def user_can(user, module_code, action='view'):
    return services.can(user, module_code, action)


@register.simple_tag
def is_access_admin(user):
    return services.is_admin(user)


@register.simple_tag
def field_access(user, model_label, field_name):
    return services.field_mode(user, model_label, field_name)


@register.simple_tag(takes_context=True)
def visible_modules(context):
    return services.visible_modules(context['user'])


@register.filter
def get_item(mapping, key):
    return mapping.get(key)


@register.simple_tag(takes_context=True)
def t(context, text):
    return tr(text, context.get('APP_LANG', 'en'))


@register.inclusion_tag('rbac/field_row.html', takes_context=True)
def render_field(context, field):
    modes = getattr(field.form, 'field_modes', {}) or {}
    field.label = tr(field.label, context.get('APP_LANG', 'en'))
    return {'field': field, 'mode': modes.get(field.name)}
