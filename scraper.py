from lxml import etree
import requests
import re
import csv
import datetime
import os


def genPyldArea (area):
  """Generates payload - area
  """

  baseUrl = 'http://www.realtylink.org/prop_search/AreaSelect.cfm?Branch=True'

  if   area.lower() == 'burnaby':
    imdp = '11'

  elif area.lower() == 'coquitlam':
    imdp = '16'

  elif area.lower() == 'newwestminster':
    imdp = '12'

  elif area.lower() == 'portcoquitlam':
    imdp = '17'

  elif area.lower() == 'richmond':
    imdp = '13'

  elif area.lower() == 'vancouver':
    imdp = '10'

  else:
    raise

  # Post and generate area ID list
  r = requests.post(baseUrl, data={'ERTA' : imdp})
  match = re.search(r'AIDL=(.*?)&', r.url, re.I)
  if match:
    AIDL = match.group(1)
  else:
    raise

  return {'imdp': imdp, 'AIDL' : AIDL}


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

  newLine =  ''.join(c if (32 <= ord(c) and ord(c) <= 255) else ' ' for c in line)
  newLine = ' '.join(newLine.strip(',').split())

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
  rExp = re.compile(r'(:|,|sqft\.?)', re.I)
  for key, val in info.items():
    if val.lower() == 'not available':
      val = 'NA'
    elif key == 'bathrooms':
      val = rExp.sub(' ', val).split()

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
      val = rExp.sub('', val).split()
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


def traversePages (area, mnage, mxage, mnbd, mnbt, ptytid, mnprc, mxprc, outDir):
  """Dive deep into the web
  """

  # Build payload
  payload = generatePayload(area, mnage, mxage, mnbd, mnbt, ptytid, mnprc, mxprc)

  first       = True
  numBytes    = 0
  listDetails = []
  nextUrl     = 'http://www.realtylink.org/prop_search/Summary.cfm'

  # Setup logging
  fName = '%s/%s_%s.csv' % (outDir, area, ptytid)
  with open('%s/log.txt' % outDir, 'a') as fLog:

    # Get pages
    while nextUrl != '':
      if first:
        page = getPage(nextUrl, payload)
        fLog.write(page.url.replace('%2C', ',') + '\n')
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

    # Number of KBs used
    fLog.write('    Number of KBs: %f\n' % (numBytes / 1024))

    # Check empty info
    if not info:
      fLog.write('    No properties were found\n')

  # Create csv
  if info:
    writeCsv(fName, info)

  return 'Ok!'


# Output directory
outDir = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
os.mkdir(outDir)

# Area list
areaList = ['burnaby', 'coquitlam', 'newwestminster', 'portcoquitlam', 'richmond', 'vancouver']

# Type list
typeList = ['apartment', 'townhouse', 'house']

# Min/max age
MNAGE = 0
MXAGE = 10

# Min bedroom
MNBD = 0

# Min bathroom
MNBT = 0

# Min/max price
MNPRC = 0
MXPRC = 450000

for AREA in areaList:
  for PTYTID in typeList:
    traversePages(AREA, MNAGE, MXAGE, MNBD, MNBT, PTYTID, MNPRC, MXPRC, outDir)

