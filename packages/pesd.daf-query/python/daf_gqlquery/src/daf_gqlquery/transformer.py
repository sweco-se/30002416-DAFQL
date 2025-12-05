"""
pesd.daf-query.DafGQLQuery implementation.
"""
import json

from fmeobjects import FMEFeature
#from fmewebservices import FMENamedConnectionManager, FMETokenConnection

from ._vendor.fmetools.http import FMERequestsSession
from ._vendor.fmetools.paramparsing import TransformerParameterParser
from ._vendor.fmetools.plugins import FMEEnhancedTransformer
from ._vendor.fmetools.webservices import FMENamedConnectionManager, FMETokenConnection

from ._vendor.graphql import parse
from ._vendor.graphql.error.syntax_error import GraphQLSyntaxError
from ._vendor.graphql.language import print_ast
from ._vendor.graphql.language.ast import ArgumentNode, IntValueNode, NameNode, OperationDefinitionNode, StringValueNode

COMPATIBLE_WEBSERVICES = ['sepesd.dafql.DAF API Key v1']

class TransformerImpl(FMEEnhancedTransformer):
    """
    The Python implementation of the DafGQLQuery transformer.
    Each instance of the transformer in the workspace has an instance of this class.
    """

    params: TransformerParameterParser
    version: int

    def setup(self, first_feature: FMEFeature):
        """
        Initialization steps based the first feature received by the transformer.
        """
        super().setup(first_feature)
        # Get transformer version from internal attribute on first feature,
        # and load its parameter definitions.
        # Note: TransformerParameterParser requires >=b24145 when running on FME Flow.
        self.version = int(first_feature.getAttribute("___XF_VERSION"))
        self.params = TransformerParameterParser(
            "pesd.daf-query.DafGQLQuery",
            version=self.version,
        )

    def receive_feature(self, feature: FMEFeature):
        """
        Receive an input feature.
        """
        # Pass internal attributes on feature into parameter parser.
        # Then get the parsed value of the First Name parameter.
        # By default, these methods assume a prefix of '___XF_'.
        self.params.set_all(feature)
        nc_name = self.params.get("CONNECTION")
        daf_register = self.params.get("REGISTER")
        
        try:
            nc = FMENamedConnectionManager().getNamedConnection(nc_name)
            assert nc is not None, f'Failed to retrieve Named Connection `{nc_name}`'
            assert type(nc) is FMETokenConnection, f'Wrong type for Named Connection `{nc_name}`, was expecting `{FMETokenConnection}` found `{type(nc)}`'
            #API_KEY
            
            request_session = FMERequestsSession()
            
            assert nc.getWebService().getName() in COMPATIBLE_WEBSERVICES, f'Wrong webservice type for Named Connection `{nc_name}`, was expecting one of `{COMPATIBLE_WEBSERVICES}` found `{nc.getWebService().getName()}`'
            api_key = nc.getKeyValues().get('API_KEY')
            
            #feature.setAttribute('_symbols{}', dir(nc))
            #feature.setAttribute('_supportQueryStringAuthorization',  str(nc.getWebService().supportQueryStringAuthorization()))
            #feature.setAttribute('_supportHeaderAuthorization',  str(nc.getWebService().supportHeaderAuthorization()))
            #feature.setAttribute('_AuthorizationQueryString', str(nc.getAuthorizationQueryString()))
            #feature.setAttribute('_daf_register', daf_register)
            
            query_doc = parse(self.params.get("QUERY"))
            assert 1 == len(query_doc.definitions), 'Only one definition is supported'
            assert type(query_doc.definitions[0]) is OperationDefinitionNode, 'Expected OperationDefinitionNode'
            assert 1 == len(query_doc.definitions[0].selection_set.selections), 'Only one selection is supported'
            selection = query_doc.definitions[0].selection_set.selections[0]
            
            args = {arg.name.value: arg for arg in selection.arguments}
            if 'first' not in args:
                args['first'] = ArgumentNode(name=NameNode(value='first'), value=IntValueNode(value=1000))
            
            url = f'{daf_register}?apiKey={api_key}'
            total_count = 0
            while True and 10000 > total_count:
                selection.arguments = tuple([*args.values()])
                
                request_body = {
                      'query': print_ast(query_doc)
                    , 'variables': {}
                }
                response = request_session.request('POST', url, json=request_body)
                response.raise_for_status()
                data = response.json()
                result = data.get('data', dict()).get(selection.name.value)
                
                for node in result.get('nodes'):
                    clone = feature.clone()
                    for k,v in node.items():
                        clone.setAttribute(k,v)
                    self.pyoutput(clone, output_tag="Output")
                    total_count += 1
            
                page_info = result.get('pageInfo')
                if not page_info.get('hasNextPage', False):
                    break
                args['after'] = ArgumentNode(name=NameNode(value='after'), value=StringValueNode(value=page_info['endCursor']))
            
            #feature.setAttribute("_selectionname", selection.name.value)
            #feature.setAttribute("_page_info", json.dumps(page_info, indent=4))
            
            #feature.setAttribute("_query", print_ast(query_doc))
            #feature.setAttribute("_request_body", json.dumps(request_body, indent=4, ensure_ascii=False))
            #feature.setAttribute("_response_body", json.dumps(data, indent=4, ensure_ascii=False))
            #self.pyoutput(feature, output_tag="Output")
        except GraphQLSyntaxError as e:
            self.reject_feature(feature, 'GraphQLSyntaxError', str(e))
        except AssertionError as e:
            self.reject_feature(feature, 'not-implemented', str(e))
        
        
