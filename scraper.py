from lxml import etree
import requests
import re


def genPyldArea (area):
  """Generates payload - area
  """

  if   area.lower() == 'burnaby':
    payload = {
      'BCD'  : 'GV',
      'imdp' : '11',
      'RSPP' : '5',
      'AIDL' : '248,249,250,251,253,254,255,256,257,258,259,260,261,856,857,858,262,263,264,265,266,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282'
    }
  elif area.lower() == 'coquitlam':
    payload = {
      'BCD'  : 'GV',
      'imdp' : '16',
      'RSPP' : '5',
      'AIDL' : '324,325,326,327,328,329,330,331,332,333,334,335,336,337,338,339,340,341,342,343,344,428,429,430'
    }
  elif area.lower() == 'newWestminster':
    payload = {
      'BCD'  : 'GV',
      'imdp' : '12',
      'RSPP' : '5',
      'AIDL' : '1539,1540,283,284,285,286,287,288,289,290,291,292,293,294,295'
    }
  elif area.lower() == 'portCoquitlam':
    payload = {
      'BCD'  : 'GV',
      'imdp' : '17',
      'RSPP' : '5',
      'AIDL' : '1541,878,345,346,347,348,349,350,351,352,433'
    }
  elif area.lower() == 'richmond':
    payload = {
      'BCD'  : 'GV',
      'imdp' : '13',
      'RSPP' : '5',
      'AIDL' : '915,916,917,918,919,920,921,922,923,924,925,926,927,928,929,930,931,932,933,934,935,936,937,938,939,940,941,942,943,310'
    }
  elif area.lower() == 'vancouver':
    payload = {
      'BCD'  : 'GV',
      'imdp' : '10',
      'RSPP' : '5',
      'AIDL' : '233,234,236,235,237,238,239,240,241,242,243,244,245,246,247,855,432'
    }
  else:
    raise

  return payload


def genPyldType (type):
  """Generates payload - type
  """

  if   type.lower() == 'apartment':
    payload = {
      'PTYTID' : 1,
    }
  elif type.lower() == 'townhouse':
    payload = {
      'PTYTID' : 2,
    }
  elif type.lower() == 'house':
    payload = {
      'PTYTID' : 5,
    }
  else:
    raise

  return payload


def generatePayload (area, mnage, mxage, mnbd, mnbt, ptytid, mnprc, mxprc):
  """Generates payload

  Args:
      area:
  Returns:
      payload
  """

  payload = {
    'SRTB'  : 'P_Price',
    'ERTA'  : 'True',
    'MNAGE' : mnage,
    'MXAGE' : mxage,
    'MNBD'  : mnbd,
    'MNBT'  : mnbt,
    'MNPRC' : mnprc,
    'MXPRC' : mxprc,
    'SCTP'  : 'RS'
  }

  return {**payload, **genPyldArea(area), **genPyldType(ptytid)}


def generateDetails (html):
  """Generates list of details URLs
  """

  baseUrl = 'http://www.realtylink.org/prop_search/Detail.cfm?'
  rExp    = re.compile(r'MLS=([a-z0-9]+)', re.I)
  details = []
  seen    = []

  listRaw = html.xpath("//@href[starts-with(., 'Detail.cfm')]")
  for raw in listRaw:
    match = rExp.search(raw)
    if match and (match.group(0) not in seen):
      seen.append(match.group(0))
      details.append(baseUrl + match.group(0))

  return details


def generateNext (html):
  """Generates next URL
  """

  baseUrl = 'http://www.realtylink.org/prop_search/'
  next    = ''

  listRaw = html.xpath("//@href[starts-with(., 'Summary.cfm')]")
  for raw in listRaw:
    if raw.endswith('Next&'):
      next = baseUrl + raw
    else:
      continue

    # Only use the first one
    break

  return next


def getPage (url, payload=None):
  """Go get page
  """

  page = requests.get(url, params=payload)
  return page


def traversePages (area, mnage, mxage, mnbd, mnbt, ptytid, mnprc, mxprc):
  """Dive deep into the web
  """

  # Build payload
  payload = generatePayload(area, mnage, mxage, mnbd, mnbt, ptytid, mnprc, mxprc)

  # Get first page
  page = getPage('http://www.realtylink.org/prop_search/Summary.cfm', payload)

  # Convert to HTML
  html = etree.HTML(page.text)

  # Parse HTML
  listDetails = generateDetails(html)
  print(len(listDetails), listDetails)

  nextUrl = generateNext(html)

  while nextUrl != '':
    page = getPage(nextUrl)
    html = etree.HTML(page.text)
    listDetails += generateDetails(html)
    nextUrl = generateNext(html)
    print(len(listDetails), listDetails)


# Search area
AREA = 'burnaby'

# Min/max age
MNAGE = 0
MXAGE = 10

# Min bedroom
MNBD = 0

# Min bathroom
MNBT = 0

# Search type
PTYTID = 'apartment'

# Min/max price
MNPRC = 200000
MXPRC = 400000


traversePages(AREA, MNAGE, MXAGE, MNBD, MNBT, PTYTID, MNPRC, MXPRC)

