if __package__:
    from .exchange import Exchange    
    from .keystore import Keystore

else:
    from exchange import Exchange    
    from keystore import Keystore

from argparse import ArgumentParser
from pyjson5 import load
from json import dumps
from sys import argv, stderr

def main():
    if "__main__" in argv[0]: argv[0] = __file__
    
    # todo: figure out how to do the subparser stuff so that two paths exist (--url url --method get | --call routine)
        # parser = ArgumentParser(description='Python Exchange CLI (pyexch)')
        # parser.add_argument('--keystore', metavar='keystore.json', required=True, help='json / json5 filename where secrets are stored (backup!)')
        # parser.add_argument('--params', metavar='params.json', help='json / json5 filename holding rest parameters / data')
        # parser.add_argument('--auth', metavar='coinbase.oauth2', help='the auth method to use from keystore.')
        # group = parser.add_mutually_exclusive_group(required=True)
        # group.add_argument('--url', metavar='https://...', help='rest http url to perform actions upon')
        # group.add_argument('--call', metavar='get_accounts', help='call method in the default client')

        # # Add subparsers for each main option
        # subparsers = parser.add_subparsers(dest='subcommand', help='sub-command help')

        # # Subparser for --url
        # parser_url = subparsers.add_parser('u', help='Sub-command for --url')
        # parser_url.add_argument('--url', metavar='https://...', required=True, help='rest http url to perform actions upon')
        # parser_url.add_argument('--method', metavar='< get, post >', default='get', help='rest http method (default:get, post)')

    parser = ArgumentParser(description='Python Exchange CLI (pyexch)', epilog='NOTE: Must name either "--call" or "--url", but not both')
    parser.add_argument('--method', metavar='<get,post,>', default='get', help='rest http method (get<default>,post,put,delete)')
    parser.add_argument('--url', metavar='https://...', help='rest http url to perform actions upon')
    parser.add_argument('--params', metavar='params.json', help='json / json5 filename holding rest parameters / data')
    parser.add_argument('--call', metavar='get_accounts', help='call method in the default client')
    parser.add_argument('--keystore', metavar='ks.json', required=True, help='json / json5 filename where secrets are stored (backup!)')
    parser.add_argument('--auth', metavar='exch.auth', help='the auth method to use from keystore.')
    
    args = parser.parse_args()
    
    if args.url and args.call:
        parser.print_help()
        exit(1)
        
    if not args.url and not args.call:
        parser.print_help()
        exit(2)
    
    params = None
    if args.params:
        with open(args.params, 'r') as pj:
            params = load(pj)

    internals = [
        'my_ipv4',
        'my_ipv6',
        'new_uuid'
    ]
                
    ex = Exchange.create(args.keystore, args.auth)
    
    if args.call:
        resp = ex._response = None
        if args.call == "update_keystore":
            newks = Keystore(args.params)
            ex.keystore.update(newks)
            ex.keystore.save()
            
        elif args.call == "print_keystore":
            ex.keystore.print()
        elif args.call in ['sort_keystore', 'sort_keyfile']:
            method = getattr(ex.keystore, args.call)
            method(args.params)
        elif args.call in internals:
            method = getattr(ex, args.call)
            print(method())
        else:
            # todo: clean this up, maybe mirror this guy as "ex.default_client" or something
            auth = ex.keystore.get('default')
            if   auth == 'coinbase.oauth2': client = ex.oa2_client
            elif auth == 'coinbase.v2_api': client = ex.v2_client
            elif auth == 'coinbase.v3_api': client = ex.v3_client
            method = getattr(client, args.call)
            resp = method(**params)
        
    if args.url:
        method = getattr(ex, args.method)
        resp = method(args.url, params)
        
    if(resp):
        print(dumps(resp, indent=2))
    elif ex._response != None:
        print("Last Response:", ex._response, file=stderr)
            
if __name__ == "__main__":
    main()
    