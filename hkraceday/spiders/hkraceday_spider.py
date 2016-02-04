import scrapy
from scrapy.loader import ItemLoader
from hkraceday.items import HkracedayItem, RunnerItem
from datetime import datetime, date

from scrapy import log
from scrapy.http import Request
from scrapy.contrib.loader.processor import TakeFirst
import re
import csv
import logging
import unicodedata
from urlparse import urljoin
from hkraceday import hkjc_utilities
import pprint
from collections import *
import operator

logger = logging.getLogger('hkraceday_application')

'''0.57.23
'''
def get_sec(s):
    l = s.split('.')
    if len(l)==3:
        return int(l[0]) * 60 + int(l[1]) * 1 + int(l[2]) * 0.01

def get_prio_val(str):
    if type(str) != type([]):
        return try_int(str)
    if str is None:
        return []
    return [int(s) for s in str.split() if s.isdigit()][0]


def cleanescapes(s):
    s = s.replace(u'\r', u'')
    s = s.replace(u'\t', u'')
    s = s.replace(u'\n', u'')
    s = s.replace(u' ', u'')
    return s
'''
use cases: u'\r\n2\r\n\t\t\t\t\t'
also remove '\xa0'
'''
def cleanstring(s):
    s = unicode(s)
    r = unicodedata.normalize('NFD', s)
    r = r.encode('ascii', 'ignore').decode('ascii')
    r = cleanescapes(r)
    r = r.replace(u'\xa0',u'')
    pattern = re.compile(r'\s+')
    return re.sub(pattern, u' ',r)

def tf(values, encoding="utf-8"):
    value = ""
    for v in values:
        if v is not None and v != "":
            value = v
            break
    return value.encode(encoding).strip()

def try_float(value):
    try:
        return float(value)
    except:
        return 0.0

def try_int(value):
    try:
        return int(value)
    except:
        return 0

ratingpat = re.compile(r'.*Rating:([0-9]{1,3}-[0-9]{1,3}),.*')
classgrouppat = re.compile(r'.*[Class|Group]([0-9]{1})$')
prizepat = re.compile(r'.*^PrizeMoney:\$([0-9]{0,1},{0,1}[0-9]{1,3},[0-9]{1,3}).*')
distancepat = re.compile(r'\D*([0-9]{3,4})M.*')
goingpat = re.compile(r'.*(Good).*')    #add goings
trackcoursepat = re.compile(r'.*(Turf, \"A\" Course).*')

class RaceItemLoader(ItemLoader):
    #default_output_processor = TakeFirst()
    # place_out = Join()
    # actualwt_out = Join()

    #runningpositions_out = Compose(dorunningpositions)
    pass

class RunnerItemLoader(ItemLoader):
    #default_output_processor = TakeFirst()
    # place_out = Join()
    # actualwt_out = Join()

    #runningpositions_out = Compose(dorunningpositions)
    pass

class HKracedaySpider(scrapy.Spider):
    name = "hkraceday"
    allowed_domains = ['racing.scmp.com', 'hkjc.com']
    #store basis for aggregate information here
    todaysrunners = defaultdict(list)   #horsecodes
    todaystrainers= defaultdict(list)
    todaysjockeys = defaultdict(list)
    todaysratingchanges = defaultdict(list)
    todaysbesttimes = defaultdict(list)
    todayspriorities = defaultdict(list)
    todaysseasonstakes = defaultdict(list)
    todaysgears = defaultdict(list)
    todaysdraws = defaultdict(list)
    todaysowners = defaultdict(list)
    todaysimportcategories = defaultdict(list)

    def __init__(self, racedate, racecoursecode, *args, **kwargs):
        assert racecoursecode in ['ST', 'HV']
        assert len(racedate) == 8 and racedate[:2] == '20'
        super(HKracedaySpider, self).__init__(*args, **kwargs) #makes sure parent is init'd

        self.hkjc_domain = 'racing.hkjc.com'
        self.domain = 'hkjc.com'
        self.racedate = racedate
        self.racedateo = datetime.strptime(self.racedate, '%Y%m%d').date()
        self.racecoursecode = racecoursecode
        self.todaysdate = datetime.today().date()
        self.inputdate = datetime.strptime(racedate, "%Y%m%d").date()
        _isit = (self.inputdate - self.todaysdate).days > 3
        self.historical = _isit
        self.tips_url = 'http://racing.scmp.com/Tips/tips.asp'
        self.hkjcraces_url = 'http://{domain}/racing/Info/Meeting/RaceCard'\
            '/English/Local/{racedate}/{coursecode}/1'.format(
                domain=self.hkjc_domain,
                racedate=racedate,
                coursecode=racecoursecode,
        )
        self.racecardpro_url = 'http://racing.scmp.com/racecardpro/racecardpro.asp'
        self.start_urls = [
            'http://racing.scmp.com/login.asp'
        ]

    def parse(self, response):
        #first of all go to get list of runners by race, noofraces
        #then get last run reminder
        # scmp comments
        return scrapy.Request(self.hkjcraces_url, callback=self.parse_hkjc_races)
        # return scrapy.Request("racing.hkjc.com/racing/english.index.aspx", callback=self.parse_frontpage)

        # if (self.inputdate - self.todaysdate).days > 3:
        #     self.historical = 1
        #     return scrapy.Request("racing.hkjc.com/racing/english.index.aspx", callback=self.parse_frontpage)
        #     return scrapy.Request(self.hkjcraces_url, callback=self.parse_hkjc_races)
        # else:
        #     return scrapy.http.FormRequest.from_response(
        #     response,
        #     formdata={'Login': 'luckyvince', 'Password': 'invader'},
        #     callback=self.after_login,
        # )

    def parse_hkjc_races(self, response):
        #HKJC racecard

        race_paths = response.xpath('//td[@nowrap="nowrap" and @width="24px"]'
            '/a/@href').extract()
        card_urls = ['http://{domain}{path}'.format(
                domain=self.hkjc_domain,
                path=path,
            ) for path in race_paths
        ] + [response.url]
        # result_urls = [_url.replace('RaceCard', 'Results') for _url in card_urls]
        for card_url in card_urls:
            if int(card_url.split('/')[-1]) > 9:
                racenumber = '{}'.format(card_url.split('/')[-1])
            else:
                racenumber = '0{}'.format(card_url.split('/')[-1])
            request = scrapy.Request(card_url, callback=self.parse_hkjc_racecard)
            request.meta.update(response.meta)
            request.meta['racenumber'] = racenumber
            request.meta['racecoursecode'] = self.racecoursecode
            request.meta['racedate'] = self.inputdate
            # item['card_url'] = card_url
            request.meta['card_url'] = card_url
            yield request
            # yield item


    def parse_hkjc_racecard(self, response):
        # print "the url {}- hist? {}".format(response.url, HKracedaySpider.historical)
        # print(response.meta)
        racenumber = response.meta['racenumber']
        try:
            raceloader = RaceItemLoader(HkracedayItem(), response=response)
            item = HkracedayItem()
            raceinfo_ = response.xpath('//table[@class="font13 lineH20 tdAlignL"]//descendant::text()[ancestor::td and normalize-space(.) != ""][position()>=2]').extract()
            if raceinfo_:
                date_racecourse_localtime = cleanstring(raceinfo_[0])
                surface_distance = raceinfo_[1].encode('utf-8').strip()
                # print "surface_distance--> {}".format(surface_distance)
                prize_rating_class = cleanstring(raceinfo_[2])
                response.meta['prizemoney'] = re.match(prizepat, prize_rating_class).group(1)
                response.meta['rating'] = re.match(ratingpat, prize_rating_class).group(1)
                response.meta['raceclass'] = re.match(classgrouppat, prize_rating_class).group(1)
                response.meta['distance'] = re.match(distancepat, surface_distance).group(1)
                response.meta['going']= re.match(goingpat, surface_distance).group(1)
                response.meta['trackcourse'] =re.match(trackcoursepat,surface_distance).group(1)

                raceloader.add_value('url', response.url)
                raceloader.add_value('rating', response.url)
                raceloader.add_value('raceclass', response.url)
                raceloader.add_value('distance', response.url)
                raceloader.add_value('going', response.url)

                # print "prize_rating_class--> {}".format(prize_rating_class)

            #horsecode horseno, draw, jockeycode trainercode, rtgdiffL1, besttimerank, seasonstakesrank, prio, gearchange? import
            #trainerrank



            runneritems = []
            '''
                todaysjockeys = defaultdict(list)
                todaysratingchanges = defaultdict(list)
                todaysbesttimes = defaultdict(list)
                todayspriorities = defaultdict(list)
                todaysseasonstakes = defaultdict(list)
                todaysgears = defaultdict(list)
                todaysowners = defaultdict(list)
                todaysimportcategories = defaultdict(list)

            '''
            for tr in response.xpath('//table[@class="draggable hiddenable"]//tr[position() > 1]'):
                # horseno, horsecode, jockeycode, seasonstakes, trainercode, priority,
                runnerloader = RaceItemLoader(RunnerItem(), response=response)
                # runneritem = RunnerItem()
                attrs = list()

                horsenumber = tr.xpath('td[1]/text()').extract()[0]
                runnerloader.add_value('horsenumber', horsenumber)
                horsecode_ = tr.xpath('td[4]/a/@href').extract()[0]
                horsecode = re.match(r"^[^\?]+\?horseno=(?P<code>\w+)'.*$",
                    horsecode_).groupdict()['code']
                # horse_url = 'http://www.hkjc.com/english/racing/horse.asp?HorseNo={}&Option=1#htop'.format(horsecode)
                # self.code_set.add(horsecode)
                self.todaysrunners[racenumber].append(horsecode)

                # horseattrs[horsecode]['horsenumber'] = horsenumber
                jockeycode_ = tr.xpath('td[7]/a/@href').extract()[0]
                jockeycode = re.match(r"^[^\?]+\?jockeycode=(?P<code>\w+)'.*",
                    jockeycode_).groupdict()['code']
                self.todaysjockeys[racenumber].append(jockeycode)

                # horseattrs[horsecode]['jockeycode'] = jockeycode
                ##TRAINER CODE
                # trainername_ = tr.xpath('td[10]/a/text()').extract()[0]
                trainercode_ = tr.xpath('td[10]/a/@href').extract()[0]
                trainercode = re.match(r"^[^\?]+\?trainercode=(?P<code>\w+)'.*",
                    trainercode_).groupdict()['code']
                self.todaystrainers[racenumber].append(trainercode)
                # horseattrs[horsecode]['trainercode'] = trainercode
                # print("trainercode:%s" % trainercode)
                # racetrainers[trainercode].extend([horsecode]) #need list here

                todaysratingchange_ = tr.xpath('td[12]/text()').extract()[0]
                self.todaysratingchanges[racenumber].append(todaysratingchange_)
                besttime_ = tr.xpath('td[15]/text()').extract()[0]
                besttime = get_sec(besttime_)
                self.todaysbesttimes[racenumber].append(besttime)
                # print(besttime)
                # racebesttimes[horsecode] = besttime

                owner_ = tr.xpath('td[22]/text()').extract()[0]
                gear_ = tr.xpath('td[21]/text()').extract()[0]

                self.todaysowners[racenumber].append(owner_)
                self.todaysgears[racenumber].append(gear_)
                # horseattrs[horsecode]['ratingchange'] = todaysrating_

                seasonstakes_ = tr.xpath('td[18]/text()').extract()[0]
                self.todaysseasonstakes[racenumber].append(seasonstakes_)
                # raceseasonstakes[horsecode] = seasonstakes_

                priority_ = tr.xpath('td[20]/text()').extract()[0].strip()
                ### DECODE priroty *\xa01 -> *1
                # racepriorities[horsecode] = priority_
                self.todayspriorities[racenumber].append(priority_)
                draw_ = tr.xpath('td[9]//text()[normalize-space()]').extract()[0]
                # draw_ = tr.xpath('td[8]/text()[normalize-space()]').extract()[0]
                draw = draw_.replace(u'\xa0', u'')
                self.todaysdraws[racenumber].append(draw_)

                importcategory_ = tr.xpath('td[25]/text()').extract()[0].strip()
                self.todaysimportcategories[racenumber].append(importcategory_)
                ##CREATE HORSECODE ATTRIBUTES
                horseattrs = dict()
                ##ADD ALL ATTRIBUTES IN HERE
                horsecodeidx = list(self.todaysrunners[racenumber]).index(horsecode)
                thistrainer = self.todaystrainers[racenumber][horsecodeidx]
                thispriority = self.todayspriorities[racenumber][horsecodeidx]
                # print thistrainer
                # print thispriority
                horseattrs = { 'trainer': thistrainer, 'priority': thispriority }
                runnerloader.add_value('horseattrs', horseattrs)
                runneritems += [runnerloader.load_item()]
                #end loop


            '''
            TODO
            AGG DATA for each horse create metrics then add metrics to horseattrs
            metrics:
            priorityrank
            besttimerank
            seasonstakesrank
            agerank
            '''
            # print self.todaysrunners[racenumber]
            # print self.todaystrainers[racenumber]

            #should return a LIST of indexes with this runner
            # stablemates_idxes = list(self.todaystrainers).index(thistrainer)
            #minus this runners index
            # stablemates_idxes = [x for x in stablemates_idxes if x != horsecodeidx]
            # self.todayspriorities[horsecodeidx]

            betterranked = 0
            # pprint.pprint(stablemates_idxes)
            # for s in stablemates_idxes:
            #     if get_prio_val(racepriorities[s]) < get_prio_val(thistrainer):
            #         betterranked+=1
            # response.meta['priorityrank'] = betterranked+1
            #
            # sorted_raceseasonstakes = sorted(raceseasonstakes.items(), key= operator.itemgetter(1), reverse=True)
            #returns list of tuples - get index of horsecode
            # prizemoneyrank = [y[0] for y in sorted_raceseasonstakes].index(horsecode)+1
            # filter racebesttimes

            # sorted_racebesttimes = sorted(racebesttimes.items(), key= operator.itemgetter(1))
            # print("best race times h:")
            # pprint.pprint(sorted_racebesttimes)
            # if not racebesttimes[horsecode]:
            #     besttimerank = [y[0] for y in sorted_racebesttimes].index(horsecode)+1
            # else:
            #     besttimerank = 99

            #use these to get prios etc..
            response.meta['todaysrunnersrace'] = self.todaysrunners[racenumber]
            response.meta['todaystrainersrace'] = self.todaystrainers[racenumber]
            # response.meta['prizemoneyrank'] = prizemoneyrank
            # response.meta['horseattrs'] = horseattrs
            # response.meta['besttimerank'] = besttimerank
            HOME_URL = "http://racing.hkjc.com/racing/english/index.aspx"
            LAST_RUN_URL = "http://racing.hkjc.com/racing/english/racing-info/last-run-reminder.aspx"
            request = scrapy.Request(LAST_RUN_URL, callback=self.parse_lastrun)
            request.meta.update(response.meta)
            request.meta['runneritems'] = runneritems
            yield request
            # yield response.meta

        except Exception, e:
            log.msg("Skipping url %s because of error: %s" % (response.url, str(e)))

    def parse_lastrun(self, response):
        #find url
        print "in last run"
        l1 = defaultdict(dict)

        print response.url

        # for tr in response.xpath("//tbody[contains(@id, 'timesheetcontent')]//tr[position()>1 and @class='highlight']"):
        #     pass
        #get race info and last updated
        racedate = response.xpath("//div[@class='racedate']//text()").extract()
        thisupdate = response.xpath("//div[@class='updatetime']//text()").extract()
        # item['updatetime'] = thisupdate
        # item['racedate'] = racedate
        for tr in response.xpath("//table[@id ='timesheettable']//tr[contains(@class,'highlight')]"):
            print "in good horses"
            # raceno = tr.xpath("td")[1].xpath("text()").extract()[0].strip()
            # horseno = tr.xpath("td")[2].xpath("text()").extract()[0].strip()
            # comment = tr.xpath("td")[11].extract()[0].strip()
            # # horseurl = tr.xpath("td")[3].xpath("a/@href").extract()[0].strip()
            # print(raceno, horseno, comment)

            # l1[horseurl]['rc'] = tr.xpath("/td[4]/text()").extract()[0]
            # l1[horseurl]['wides'] = tr.xpath("/td[11]/ul//li/text()").extract()[0]
            # l1[horseurl]['comment'] = tr.xpath("/td[12]/text()").extract()[0]
        # pprint.pprint(l1)
        # yield item
        yield response.meta

    '''
    todo: vet and tw
    sincelastrun averagebetweenruns
    metrics?
    scmp comments or ?http://racing.scmp.com/odds/oddstrend.asp
    '''

    def after_login(self, response):
        if "authentication failed" in response.body:
            self.logger.error("Login failed")
            return
        else:
            return scrapy.Request(self.racecardpro_url, callback=self.parse_racecardpro_url)


    def parse_frontpage(self, response):
        print(response.url)
        return
