import os
import sys
import json
import click
import getpass
from bitcoinecdsa import privkey_to_address, pubkey
from bitcoinaddress import check_bitcoin_address
from validate import validate_enrollment
from user import User, Base
from util import unique
from document import Document


def shorten(text, length=60):
    if len(text) > length - 3 and len(text) < length:
        return text[0:length-1]
    elif len(text) > length - 3:
        return text[0:length-1] + '...'
    else:
        return text

def short_addr(text):
    return text[0:10] + '...' + text[-8:]

def hilight(string, status, bold):
    attr = []
    if status:
        # green
        attr.append('32')
    else:
        # red
        attr.append('31')
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)


def job_link(j):
    return '<a href="/job/%s">%s</a>' % (j['Job ID'], j['Job name'])


def get_choice(choices, name):
    choice = -1
    while(choice >= len(choices) or choice < 0) and choice != 'q':
        choice = click.prompt('Choose a '+name+' (q to quit)', type=str)
        try:
            choice = int(choice)
        except:
            choice = choice
    return choice


def btc_addr_prompt(name):
    title = hilight(name.capitalize() + " Bitcoin address", True, True)
    addr = click.prompt(title, type=str)
    while not check_bitcoin_address(addr.strip()):
        addr = click.prompt("Invalid.\n" + title, type=str)
    return addr


def btc_privkey_prompt(name, addr=None):
    title = hilight(name.capitalize() + " Bitcoin private key: ", True, True)
    privkey = getpass.getpass(title)
    if addr:
        while privkey_to_address(privkey.strip()) != addr:
            privkey = getpass.getpass("Not valid or corresponding to target address.\n" + title)
    else:
        while not privkey_to_address(privkey.strip()):
            privkey = getpass.getpass("Invalid private key.\n" + title)
    return privkey.strip()


def identity_prompt(rein):
    users = rein.session.query(User).filter(User.enrolled == True,
                                            User.testnet == rein.testnet).all()
    user_count = len(users) 
    index = 0
    i = 0
    for user in users:
        click.echo('%s - %s' % (str(index + 1), user.name))
        index += 1
    while i > user_count or i < 1:
        i = click.prompt('Please choose an identity', type=int)
    rein.user = rein.session.query(User).filter(User.name == users[i - 1].name).first()
    return rein.user


def create_account(rein):
    Base.metadata.create_all(rein.engine)
    name = click.prompt(hilight("\nEnter name or handle", True, True), type=str)
    contact = click.prompt(hilight("Email or BitMessage address", True, True), type=str)
    click.echo('\nIn Rein, all activity - including setting contact info, creating\n'
               'a job, or getting paid - is linked to a master Bitcoin address.\n\n'
               'You should keep the private key that corresponds to this address\n'
               'offline unless you need to update your main user record.\n')
    maddr = btc_addr_prompt('Master')

    click.echo('\nInstead of the Master address, python-rein uses another address\n'
               'that you authorize for day-to-day activities. The private key for\n'
               'this address will be stored locally to sign documents and auth to\n'
               'microhosting servers.\n\n'
               'If this computer or its local database are lost or stolen, you\n'
               'will use the private key for your master address to revoke and\n'
               'replace the delegate address.\n')
    daddr = btc_addr_prompt('Delegate')
    click.echo('\nIn order for python-rein to authenticate on your behalf, it\n'
               'will store the delegate\'s private key in the local database.\n')
    dkey = btc_privkey_prompt('Delegate', daddr)
    click.echo('\nRein requires three parties to every transaction: a job creator,\n'
               'mediator and worker. Mediators are called upon to resolve disputes\n'
               'and may use their delegate key to do so.\n\n'
               'In exchange, mediators may charge a fee, the funds for which  are\n'
               'sent to an address that ensures those funds will go only to the\n'
               'mediator.\n')
    will_mediate = click.confirm(hilight('Are you willing to mediate?', True, True), default=False)
    mediator_fee = 1
    if will_mediate:
        mediator_fee = click.prompt(hilight("Mediator fee (%)", True, True), default=1.0)
    new_identity = User(name, contact, maddr, daddr, dkey, will_mediate, mediator_fee, rein.testnet)
    rein.session.add(new_identity)
    rein.session.commit()
    data = {'name': name,
            'contact': contact,
            'maddr': maddr,
            'daddr': daddr,
            'dkey': dkey,
            'will_mediate': will_mediate,
            'mediator_fee': mediator_fee,
            'testnet': rein.testnet}
    if not os.path.isfile(rein.backup_filename):
        f = open(rein.backup_filename, 'w')
        try:
            f.write(json.dumps(data))
            click.echo("Backup saved successfully to %s" % rein.backup_filename)
        except:
            raise RuntimeError('Problem writing user details to json backup file.')
        f.close()
    else:
        click.echo("Backup file already exists. Please run with --backup to save "
                   "user details to file.")
    rein.user = new_identity
    return rein.user


def import_account(rein):
    Base.metadata.create_all(rein.engine)
    backup_filename = click.prompt("Enter backup file name", type=str, default=rein.backup_filename)
    f = open(backup_filename, 'r')
    try:
        data = json.loads(f.read())
    except:
        raise RuntimeError('Backup file %s not valid json.' % backup_filename)
    if not check_bitcoin_address(data['maddr']) or not check_bitcoin_address(data['daddr']):
        click.echo("Invalid Bitcoin address(es) in backup file.")
        sys.exit()
    if 'testnet' not in data:
        click.echo("Warning: testnet not set in backup. Setting to "+ str(rein.testnet))
        data['testnet'] = rein.testnet
    new_identity = User(data['name'],
                        data['contact'],
                        data['maddr'],
                        data['daddr'],
                        data['dkey'],
                        data['will_mediate'],
                        data['mediator_fee'],
                        data['testnet'])
    rein.session.add(new_identity)
    rein.session.commit()
    rein.user = new_identity
    return rein.user


def build_enrollment(rein):
    user = rein.user
    mediator_extras = ''
    if user.will_mediate:
        mediator_extras = "\nMediator public key: %s\nMediator fee: %s%%" % \
                          (pubkey(user.dkey), user.mediator_fee)
    enrollment = "Rein User Enrollment\nUser: %s\nContact: %s\nMaster signing address: %s" \
                 "\nDelegate signing address: %s\nWilling to mediate: %s%s" % \
                 (user.name, user.contact, user.maddr, user.daddr, user.will_mediate, mediator_extras)
    if rein.testnet:
        enrollment += '\nTestnet: True'
    return enrollment


def build_enrollment_from_dict(data):
    mediator_extras = ''
    if data['will_mediate']:
        mediator_extras = "\nMediator public key: %s\nMediator fee: %s%%" % \
                          (pubkey(data['dkey']), data['mediator_fee'])
    enrollment = "Rein User Enrollment\nUser: %s\nContact: %s\nMaster signing address: %s" \
                 "\nDelegate signing address: %s\nWilling to mediate: %s%s" % \
                 (data['name'], data['contact'], data['maddr'], data['daddr'], data['will_mediate'], mediator_extras)
    if data['testnet']:
        enrollment += '\nTestnet: True'
    return enrollment


def enroll(rein):
    Base.metadata.create_all(rein.engine)
    enrollment = build_enrollment(rein)
    f = open(rein.enroll_filename, 'w')
    f.write(enrollment)
    f.close()
    click.echo("%s\n" % enrollment)
    done = False
    while not done:
        filename = click.prompt(hilight("File containing signed statement", True, True), type=str, default=rein.sig_enroll_filename)
        if os.path.isfile(filename):
            done = True
        else:
            click.echo("File not found. Please check the file name and location and try again.")
    f = open(filename, 'r')
    signed = f.read()
    res = validate_enrollment(signed)
    if res:
        User.set_enrolled(rein, user)
        # insert signed document into documents table as type 'enrollment'
        document = Document(rein, 'enrollment', signed, sig_verified=True, testnet=rein.testnet)
        rein.session.add(document)
        rein.session.commit()
    return res


def mediator_prompt(rein, eligible_mediators):
    mediators = unique(eligible_mediators, 'Mediator public key')
    key = pubkey(rein.user.dkey)
    i = 0
    for m in mediators:
        if m["Mediator public key"] == key:
            mediators.remove(m)
            continue
        click.echo('%s - %s - Fee: %s - Public key: %s' % (str(i), m['User'], m['Mediator fee'], m['Mediator public key']))
        i += 1
    if len(mediators) == 0:
        click.echo("None found.")
        return None
    choice = get_choice(mediators, 'mediator')
    if choice == 'q':
        return False
    return mediators[choice]


# called in offer()
def bid_prompt(rein, bids):
    """
    Prompts user to choose a bid on one of their jobs. This means they should be the job creator and
    not the worker or mediator.
    """
    i = 0
    valid_bids = []
    key = pubkey(rein.user.dkey)
    for b in bids:
        if 'Description' not in b or b['Job creator public key'] != key:
            continue 
        click.echo('%s - %s - %s - %s - %s bitcoin' % (str(i), b['Job name'], b["Worker"],
                                                  shorten(b['Description']), b['Bid amount (BTC)']))
        valid_bids.append(b)
        i += 1
    if len(valid_bids) == 0:
        click.echo('No bids available.')
        return None
    choice = get_choice(valid_bids, 'bid')
    if choice == 'q':
        click.echo('None chosen.')
        return False
    bid = valid_bids[choice]
    click.echo('You have chosen %s\'s bid.\n\nFull description: %s\nBid amount (BTC): %s\n\nPlease review carefully before accepting. (Ctrl-c to abort)' % 
               (bid['Worker'], bid['Description'], bid['Bid amount (BTC)']))
    return bid


def job_prompt(rein, jobs):
    """
    Prompt user for jobs they can bid on. Filters out jobs they created or are mediator for.
    """
    key = pubkey(rein.user.dkey)
    valid_jobs = []
    for j in jobs:
        if j['Job creator public key'] != key and j['Mediator public key'] != key:
            valid_jobs.append(j)
    if len(valid_jobs) == 0:
        click.echo('None found.')
        return None

    i = 0
    for j in valid_jobs:
        click.echo('%s - %s - %s - %s' % (str(i), j["Job creator"],
                                          j['Job name'], shorten(j['Description'])))
        i += 1
    choice = get_choice(valid_jobs, 'job')
    if choice == 'q':
        return False
    job = valid_jobs[choice]
    click.echo('You have chosen a Job posted by %s.\n\nFull description: %s\n\nPlease pay attention '
               'to each requirement and provide a time frame to complete the job. (Ctrl-c to abort)\n' % 
               (job['Job creator'], job['Description']))
    return job


def delivery_prompt(rein, choices, detail='Description'):
    choices = unique(choices, 'Job ID')
    i = 0
    for c in choices:
        if 'Bid amount (BTC)' not in c:
            continue
        if detail in c:
            click.echo('%s - %s - %s BTC - %s' % (str(i), c['Job name'], c['Bid amount (BTC)'], shorten(c[detail])))
        else:
            click.echo('%s - %s - %s BTC - %s' % (str(i), c['Job name'], c['Bid amount (BTC)'], shorten(c['Description'])))
        i += 1
    choice = get_choice(choices, 'job')
    if choice == 'q':
        return None
    chosen = choices[choice]
    click.echo('You have chosen to post deliverables. The following is from your winning bid.'
               '\n\nDescription: %s\n\nPlease review carefully before posting deliverables. '
               'This will be public and reviewed by mediators if disputed. (Ctrl-c to abort)\n' % 
               (chosen['Description'],))
    return chosen


def accept_prompt(rein, choices, detail='Description'):
    i = 0
    click.echo("Offers and Deliveries")
    click.echo("---------------------")
    for c in choices:
        if 'Primary escrow redeem script' not in c:
            continue
        if detail in c:
            click.echo('%s: %s - %s - %s - %s' % (c['state'].title(), str(i),
                        c['Job name'], c['Job ID'], shorten(c[detail])))
        else:
            click.echo('%s: %s - %s - %s - %s' % (c['state'].title(), str(i),
                        c['Job name'], c['Job ID'], shorten(c['Description'])))
        i += 1
    choice = get_choice(choices, 'delivery or offer')
    if choice == 'q':
        return None
    chosen = choices[choice]
    if detail in chosen:
        contents = chosen[detail]
    else:
        contents = chosen['Description']
    click.echo('You have chosen to accept the following deliverables. \n\n%s: %s\nAccepted Bid amount (BTC): %s\n'
               'Primary escrow redeem script: %s\n'
               'Worker address: %s\n\n'
               'Mediator escrow redeem script: %s\n'
               'Mediator address: %s\n'
               '\nPlease review carefully before accepting. Once you upload your signed statement, the mediator should no '
               'longer provide a refund. (Ctrl-c to abort)\n' % 
               (detail,
                contents, chosen['Bid amount (BTC)'],
                chosen['Primary escrow redeem script'],
                pubkey_to_address(chosen['Worker public key']),
                chosen['Mediator escrow redeem script'],
                pubkey_to_address(chosen['Mediator public key'])
               )
              )
    return chosen


def dispute_prompt(rein, choices, detail='Description'):
    i = 0
    for c in choices:
        if 'Primary escrow redeem script' not in c:
            continue
        if detail in c:
            click.echo('%s - %s - %s - %s' % (str(i), c['Job name'], c['Job ID'], shorten(c[detail])))
        else:
            click.echo('%s - %s - %s - %s' % (str(i), c['Job name'], c['Job ID'], shorten(c['Description'])))
        i += 1
    choice = get_choice(choices, 'job')
    if choice == 'q':
        return None
    chosen = choices[choice]
    if detail in chosen:
        contents = chosen[detail]
    else:
        contents = chosen['Description']
    click.echo('You have chosen to dispute the following deliverables. \n\n%s: %s\n\nPlease provide as much detail as possible. '
               'For the primary payment, you should build and sign one that refunds you at %s. (Ctrl-c to abort)\n' % 
               (detail, contents, rein.user.daddr))
    return chosen


def resolve_prompt(rein, choices, detail='Dispute detail'):
    i = 0
    for c in choices:
        if 'Primary escrow redeem script' not in c:
            continue
        click.echo('%s - %s - %s - %s' % (str(i), c['Job name'], c['Job ID'], shorten(c[detail])))
        i += 1
    choice = get_choice(choices, 'dispute')
    if choice == 'q':
        return None
    chosen = choices[choice]
    click.echo('You have chosen to resolve this dispute. \n\n%s: %s\n\n'
               'For the mediator payment, you should build and sign one that pays you at %s. (Ctrl-c to abort)\n' %
               (detail, chosen[detail], rein.user.daddr))
    return chosen
