from django.conf.urls import patterns, include, url
from django.views.generic.base import TemplateView
from pombola.kenya.views import KEPersonDetail, KEPersonDetailAppearances, KEHelpApiView

from .views import (CountyPerformanceView, CountyPerformanceSenateSubmission,
    CountyPerformancePetitionSubmission, CountyPerformanceShare,
    CountyPerformanceSurvey, EXPERIMENT_DATA, ThanksTemplateView,
    ShujaazFinalistsView
)

urlpatterns = patterns('',
    url(r'^shujaaz$', ShujaazFinalistsView.as_view(), name='shujaaz-finalists'),
    url(r'^shujaaz-voting$', TemplateView.as_view(template_name='shujaaz-voting.html'), name='shujaaz-voting'),
    url(r'^intro$',                TemplateView.as_view(template_name='intro.html') ),
    url(r'^register-to-vote$',     TemplateView.as_view(template_name='register-to-vote.html') ),
    url(r'^find-polling-station$', TemplateView.as_view(template_name='find-polling-station.html') ),
    url(r'^person/(?P<slug>[-\w]+)/$',
        KEPersonDetail.as_view(), name='person'),
    url(r'^person/(?P<slug>[-\w]+)/appearances/$',
        KEPersonDetailAppearances.as_view(sub_page='appearances'),
        name='person'),
    url(r'^help/api/?$',
        KEHelpApiView.as_view() )
)

# Create the two County Performance pages:

for experiment_slug in ('mit-county', 'mit-county-larger'):
    base_name = EXPERIMENT_DATA[experiment_slug]['base_view_name']
    base_path = r'^' + base_name
    view_kwargs = {'experiment_slug': experiment_slug}
    urlpatterns.append(
        url(base_path + r'$',
            CountyPerformanceView.as_view(**view_kwargs),
            name=base_name)
    )

    for name, view in (
        ('senate', CountyPerformanceSenateSubmission),
        ('petition', CountyPerformancePetitionSubmission)):

        urlpatterns += (
            url(base_path + r'/{0}$'.format(name),
                view.as_view(**view_kwargs),
                name=(base_name + '-{0}-submission'.format(name))),
            url(base_path + r'/{0}/thanks$'.format(name),
                ThanksTemplateView.as_view(
                    base_view_name=base_name,
                    template_name=('county-performance-{0}-submission.html'.format(name))
                )),
        )

    urlpatterns += (
        url(base_path + r'/share',
            CountyPerformanceShare.as_view(**view_kwargs),
            name=(base_name + '-share')),
        url(base_path + r'/survey',
            CountyPerformanceSurvey.as_view(**view_kwargs),
            name=(base_name + '-survey')),
    )
