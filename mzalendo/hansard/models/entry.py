import re

from django.db import models
from django.core.urlresolvers import reverse

from core.models import Person
from hansard.models import Sitting, Alias


class EntryQuerySet(models.query.QuerySet):
    def monthly_appearance_counts(self):
        """return an array of hasher for date ad counts for each month"""

        # would prefer to do this as a single query but I can't seem to make the ORM do that.

        dates = self.dates('sitting__start_date','month', 'DESC' )
        counts = []
        
        for d in dates:
            qs = self.filter(sitting__start_date__month=d.month, sitting__start_date__year=d.year )
            counts.append(
                dict( date=d, count=qs.count() )
            )

        return counts
        
    def unassigned_speeches(self):
        """All speeches that do not have a speaker assigned"""
        return self.filter(
            speaker__isnull = True,
            type            = 'speech',
        ).exclude(
            speaker_name = '',
        )

class EntryManager(models.Manager):
    def get_query_set(self):
        return EntryQuerySet(self.model)
    

class Entry(models.Model):
    """Model for representing an entry in Hansard - speeches, headings etc"""

    type_choices = (
        ('heading', 'Heading'),
        ('scene',   'Description of event'),
        ('speech',  'Speech'),
        ('other',   'Other'),
    )

    type          = models.CharField( max_length=20, choices=type_choices )
    sitting       = models.ForeignKey( Sitting )

    # page_number is the page that this appeared on in the source.
    page_number   = models.IntegerField( blank=True )
    
    # Doesn't really mean anything - just a counter so that for each sitting we
    # can display the entries in the correct order. 
    text_counter  = models.IntegerField()

    # Speakers only apply to the 'speech' type. For those we should always have
    # a name and possibly a title. Other code may then take those and try to
    # link the speech up to a person.
    speaker_name  = models.CharField( max_length=200, blank=True )
    speaker_title = models.CharField( max_length=200, blank=True )
    speaker       = models.ForeignKey( Person, blank=True, null=True, related_name='hansard_entries' )

    # What was actually said
    content       = models.TextField()

    objects = EntryManager()

    def __unicode__(self):
        return "%s: %s" % (self.type, self.content[:100])
    
    def get_absolute_url(self):
        url = reverse(
            'hansard:sitting_view',
            kwargs={ 'pk': self.sitting.id },
        )
        return "%s#entry-%u" % (url, self.id)


    class Meta:
        ordering = ['sitting', 'text_counter']
        app_label = 'hansard'
        verbose_name_plural = 'entries'
        
    @classmethod
    def assign_speakers(cls):
        """Go through all entries and assign speakers"""
        
        entries = cls.objects.all().unassigned_speeches()
        
        # create an in memory cache of speaker names and the sitting dates, to
        # avoid hitting the db as badly with all the repeated requests
        cache = {}

        for entry in entries:
            # print '--------- ' + entry.speaker_name + ' ---------'

            cache_key = "%s-%s" % (entry.sitting.start_date, entry.speaker_name)

            if cache_key in cache:
                speakers = cache[cache_key]
            else:
                speakers = entry.possible_matching_speakers( create_alias=True )
                cache[cache_key] = speakers

            if len(speakers) == 1:
                speaker = speakers[0]
                entry.speaker = speaker
                entry.save()                
                

    def possible_matching_speakers(self, create_alias=False):
        """
        Return array of person objects that might be the speaker.

        If 'create_alias' is True (False by default) and the name cannot be
        ignored then an entry will be made in the alias table that so that the
        alias is inspected by an admin.
        """

        name = self.speaker_name
        name = Alias.clean_up_name( name )
        
        # First check for a matching alias that is not ignored
        try:
            alias = Alias.objects.get( alias=name )
            
            if alias.person and not alias.ignored:
                return [ alias.person ]
            else:
                return []

        except Alias.DoesNotExist:
            # drop the prefix
            stripped_name = re.sub( r'^\w+\.\s', '', name )
            
            person_search = (
                Person
                .objects
                .all()
                .is_mp( when=self.sitting.start_date )
                .filter(legal_name__icontains=stripped_name)
            )
            
            results = person_search.all()[0:]
            
            if create_alias and not len(results) == 1 and not Alias.can_ignore_name(name):
                # create an entry in the aliases table if one is needed
                Alias.objects.create(
                    alias   = name,
                    ignored = False,
                    person  = None,
                )
            
            return results


