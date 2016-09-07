from lxml import etree
import requests
import re
import csv


def genPyldArea (area):
  """Generates payload - area
  """

  if   area.lower() == 'burnaby':
    payload = {
      'imdp' : '11',
      'AIDL' : '248,249,250,251,253,254,255,256,257,258,259,260,261,856,857,858,262,263,264,265,266,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282'
    }
  elif area.lower() == 'coquitlam':
    payload = {
      'imdp' : '16',
      'AIDL' : '324,325,326,327,328,329,330,331,332,333,334,335,336,337,338,339,340,341,342,343,344,428,429,430'
    }
  elif area.lower() == 'newwestminster':
    payload = {
      'imdp' : '12',
      'AIDL' : '1539,1540,283,284,285,286,287,288,289,290,291,292,293,294,295'
    }
  elif area.lower() == 'portcoquitlam':
    payload = {
      'imdp' : '17',
      'AIDL' : '1541,878,345,346,347,348,349,350,351,352,433'
    }
  elif area.lower() == 'richmond':
    payload = {
      'imdp' : '13',
      'AIDL' : '915,916,917,918,919,920,921,922,923,924,925,926,927,928,929,930,931,932,933,934,935,936,937,938,939,940,941,942,943,310'
    }
  elif area.lower() == 'vancouver':
    payload = {
      'imdp' : '10',
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
    'SCTP'  : 'RS',
    'BCD'   : 'GV',
    'RSPP'  : '5'
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
      break # Only use the first one

  return next


def getPage (url, payload=None):
  """Go get page
  """

  page = requests.get(url, params=payload)

  return page


def stripChar (line):
  """Strip unwanted characters from line
  """

  newLine =  ''.join(c for c in line if (c.isalnum() or (c in ' \'/!:",.')))
  newLine = ' '.join(newLine.split())
  if newLine.endswith(','):
    newLine = newLine[:-1]

  return newLine


def parseInfo (infoDesc, listInfo):
  """Parse main list of info
  """

  # Initialize dictionary
  info = {d: 'NA' for d in infoDesc}

  # Find starting index and description
  for i, val in enumerate(listInfo):
    if (val != '') and (not val.startswith(':')):
      if val.lower() == 'mls':
        # No description
        info['description'] = 'NA'
      else:
        info['description'] = listInfo[i]
        i += 1 # To re-align MLS
      break

  # Fill dictionary
  for key, val in zip(listInfo[i::2], listInfo[i+1::2]):
    key = key.lower().replace(':', '')

    for d in infoDesc:
      if d == key:
        info[d] = val
        break

  return info


def parsePage (html):
  """Parse page
  """

  infoDesc = [
    'mls',
    'finished floor area',
    'property type',
    'lot frontage',
    'basement',
    'lot depth',
    'bedrooms',
    'age',
    'bathrooms',
    'maintenance fee'
  ]

  info = {}

  # Get address and price
  listRaw = html.xpath('//b/text()')
  listRaw = [stripChar(l) for l in listRaw]
  info['address'] = listRaw[1]
  info['price']   = listRaw[2]

  # Get features
  listRaw = html.xpath('//li/text()')
  listRaw = [stripChar(l).capitalize() for l in listRaw]
  info['features'] = ', '.join(sorted(listRaw))

  # Get other info
  listRaw = html.xpath('//font/text()')
  listRaw = [stripChar(l) for l in listRaw]
  info = {**info, **parseInfo(infoDesc, listRaw)}

  # Clean up
  for key, val in info.items():
    if   val.lower() == 'not available':
      val = 'NA'
    elif key == 'bathrooms':
      val = val.replace(':', ' ').replace(',', ' ').split()

      try:
        t = int(val[1])
      except:
        t = 0

      try:
        h = int(val[3])
      except:
        h = 0

      val = t + (h*0.5)
    elif key not in ['address', 'description', 'features']:
      val = val.replace(',', '')
      val = [w for w in val.split() if w not in ['sqft', 'sqft.']]
      val = ' '.join(val)

    info[key] = val

  return info


def writeCsv (fName, listDict):
  """Turn list of dictionary into CSV
  """

  # Open file
  with open(fName, 'w', newline='') as csvfile:
    cwr = csv.writer(csvfile)

    # Get header
    keys = [k.title() for k in list(listDict[0])]
    keys = sorted(keys)
    cwr.writerow(keys)

    # Build/write rows
    for d in listDict:
      row = [d[k.lower()] for k in keys]
      cwr.writerow(row)

  return 'Ok!'


def traversePages (area, mnage, mxage, mnbd, mnbt, ptytid, mnprc, mxprc, fName):
  """Dive deep into the web
  """

  # Build payload
  payload = generatePayload(area, mnage, mxage, mnbd, mnbt, ptytid, mnprc, mxprc)

  first       = True
  numBytes    = 0
  listDetails = []
  nextUrl     = 'http://www.realtylink.org/prop_search/Summary.cfm'

  # Get pages
  while nextUrl != '':
    if first:
      page = getPage(nextUrl, payload)
      print(page.url)
      first = False
    else:
      page = getPage(nextUrl)

    # Calculate number of bytes
    numBytes += len(page.text)

    # Convert to HTML
    html = etree.HTML(page.text)

    # Parse HTML
    listDetails += generateDetails(html)
    nextUrl = generateNext(html)

  # Get each page with details
  info = []
  for detUrl in listDetails:
    page = getPage(detUrl)
    numBytes += len(page.text)
    html = etree.HTML(page.text)
    info.append(parsePage(html))
    info[-1]['url'] = page.url

  # Number of MBs used
  print('Number of KBs:', numBytes / 1024.0)

  # Create csv
  writeCsv(fName, info)

  return 'Ok!'


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
MXPRC = 500000


traversePages(AREA, MNAGE, MXAGE, MNBD, MNBT, PTYTID, MNPRC, MXPRC, '_'.join([AREA, PTYTID]) + '.csv')

