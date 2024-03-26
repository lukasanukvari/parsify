import requests

from json import load, dumps


class Handbook:
    def __init__(self, book: str | dict):
        self.handbook: dict = book if type(book) is dict else self.read_json(book)
        self.__validate_handbook()

    @staticmethod
    def read_json(file: str):
        with open(file=file, mode='r') as f:
            return load(f)

    def __validate_handbook(self):
        def raise_invalid_handbook():
            raise Exception('Invalid Handbook.')

        step_musts = (
            'name', 'chain_id',
            'url', 'method',
            'output_path', 'output'
        )
        step_optionals = (
            'headers', 'parameters',
            'payload', 'payload_type',
            'dynamic_variables', 'iterables_order'
        )

        if 'parsers' not in self.handbook:
            raise_invalid_handbook()
        if type(self.handbook['parsers']) is not list:
            raise_invalid_handbook()

        for parser in self.handbook['parsers']:
            if 'scope' not in parser or 'steps' not in parser:
                raise_invalid_handbook()
            if type(parser['scope']) is not str or type(parser['steps']) is not list:
                raise_invalid_handbook()

            for step in parser['steps']:
                if type(step) is not dict:
                    raise_invalid_handbook()

                for mst in step_musts:
                    if mst not in step:
                        raise_invalid_handbook()

                for opt in step_optionals:
                    if opt not in step:
                        step[opt] = None

                if step['dynamic_variables']:
                    if 'iterables' not in step['dynamic_variables']:
                        step['dynamic_variables']['iterables'] = None
                    if 'standard' not in step['dynamic_variables']:
                        step['dynamic_variables']['standard'] = None

                if 'is_chain_final' not in step['output']:
                    step['output']['is_chain_final'] = False
                if 'is_parser_final' not in step['output']:
                    step['output']['is_parser_final'] = False

                if 'key' not in step['output']:
                    step['output']['key'] = None

    def __str__(self):
        return dumps(self.handbook, indent=4)


class Engine(Handbook):
    def __init__(self, handbook: Handbook | str | dict):
        if type(handbook) is not Handbook:
            Handbook.__init__(self, book=handbook)
        else:
            self.handbook: dict = handbook

        self.current_parser: dict = self.handbook['parsers'][0]
        self.current_step: dict = self.current_parser['steps'][0]

        self.results = dict()

        self.__reset_cache()
        self.__reset_icfg()

    def stepshot(
            self,
            step: str | dict = None,
            increment_iterables: list = None,
            reset_iterables: list = None
    ) -> list | int:
        """Runs a single step in the parser.
        :param step: If dictionary provided, current_step attribute will be set to it.
            If string provided, current_step attribute will be set to
            the step with provided name in a handbook.
            If not provided, current_step attribute will not be changed.
        :param increment_iterables: Iterables that should be incremented.
        :param reset_iterables: Iterables that should be reset.
        :return: Collected data list or -1 (stop status).
        """
        self.__set_step(step=step)
        self.__set_icfg(increment_iterables=increment_iterables, reset_iterables=reset_iterables)

        try:
            self.__set_variables()
        except IndexError:
            return -1

        try:
            response = self.__send_request().json()
        except (KeyError, requests.exceptions.JSONDecodeError):
            return -1
        else:
            if not response:
                return -1

        return self.__output_handler(response=response)

    def chainshot(self, chain_id: int):
        """Runs a full chain in parser.
        :param chain_id: ID of the chain that should be executed.
        :return: None
        """
        steps = [step for step in self.current_parser['steps'] if step['chain_id'] == chain_id]
        s_len = len(steps)
        iterables_order = steps[0]['iterables_order']

        self.__set_step(step=steps[0]['name'])

        nstep = 0
        cur_it = 0
        first_time = True

        if iterables_order:
            while cur_it < len(iterables_order):
                if first_time:
                    incr_its = None
                    reset_its = None
                    first_time = False
                else:
                    incr_its = iterables_order[cur_it]
                    reset_its = iterables_order[:cur_it]

                response = self.stepshot(
                    step=steps[nstep]['name'],
                    increment_iterables=incr_its,
                    reset_iterables=reset_its
                )

                if response == -1:
                    cur_it += 1
                else:
                    cur_it = 0

                nstep = (nstep + 1) if nstep < (s_len - 1) and response != -1 else 0
        else:
            for step in steps:
                self.stepshot(step=step['name'])

        for st in steps:
            if st['output']['is_parser_final']:
                self.results[self.current_parser['scope']] = self.__current_cache[st['name']]

    def scopeshot(self, parser: str | dict = None) -> list:
        """Runs a full parser of the provided scope.
        :param parser: Scope name (str) or parser object (dict) that should be executed.
            If None, method will use the parser object from current_parser attribute.
        :return: Final data list collected from the parser.
        """
        self.__reset_cache()
        self.__set_parser(parser=parser)

        chain_ids = sorted(list({step['chain_id'] for step in self.current_parser['steps']}))

        for chid in chain_ids:
            self.chainshot(chain_id=chid)

        return self.results[self.current_parser['scope']]

    def parse(self) -> dict:
        """Runs all the parsers.
        :return: Final dictionary of results collected from parsers.
        """
        scopes = [p['scope'] for p in self.handbook['parsers']]
        for scope in scopes:
            self.scopeshot(parser=scope)

        return self.results

    def __send_request(self) -> requests.Response:
        return requests.request(
            method=self.current_step['method'],
            url=self.current_step['url'],
            headers=self.current_step['headers'],
            params=self.current_step['parameters'],
            json=self.current_step['payload'] if self.current_step['payload_type'] == 'json' else None,
            data=self.current_step['payload'] if self.current_step['payload_type'] == 'data' else None
        )

    def __set_parser(self, parser: str | dict | None):
        if parser:
            if type(parser) is str:
                for p in self.handbook['parsers']:
                    if type(parser) is str and p['scope'] == parser:
                        self.current_parser = p
                        break
                else:
                    raise ValueError(f'Parser with the scope: "{parser}" could not be found.')
            else:
                self.current_parser = parser

    def __set_step(self, step: str | dict | None):
        if step:
            if type(step) is str:
                for s in self.current_parser['steps']:
                    if type(step) is str and s['name'] == step:
                        self.current_step = s
                        break
                else:
                    raise ValueError(f'Step with the name: "{step}" could not be found.')
            else:
                self.current_step = step

    def __set_icfg(self, increment_iterables: list = None, reset_iterables: list = None):
        if not self.current_step['dynamic_variables']:
            return
        if not self.current_step['dynamic_variables']['iterables']:
            return

        if reset_iterables or not self.__current_icfg:
            for i, v in self.current_step['dynamic_variables']['iterables'].items():
                if not self.__current_icfg:
                    self.__current_icfg[i] = dict()

                    for k in v.keys():
                        if type(v[k]) is not dict:
                            self.__current_icfg[i][k] = 0
                        else:
                            self.__current_icfg[i][k] = v[k]['start']
                else:
                    for k in reset_iterables:
                        k_list = list([k]) if type(k) is not list else k

                        for j in k_list:
                            if type(v[j]) is not dict:
                                self.__current_icfg[i][j] = 0
                            else:
                                self.__current_icfg[i][j] = v[j]['start']
        else:
            for i, v in self.current_step['dynamic_variables']['iterables'].items():
                if not increment_iterables:
                    for k in v.keys():
                        if type(v[k]) is not dict:
                            self.__current_icfg[i][k] += 1
                        else:
                            self.__current_icfg[i][k] += v[k]['increment']
                else:
                    if type(increment_iterables) is str:
                        iterables_list = list([increment_iterables])
                    else:
                        iterables_list = increment_iterables

                    for it in iterables_list:
                        its_list = list([it]) if type(it) is str else it
                        for il in its_list:
                            if type(v[il]) is not dict:
                                self.__current_icfg[i][il] += 1
                            else:
                                self.__current_icfg[i][il] += v[il]['increment']

    def __set_variables(self):
        if not self.current_step['dynamic_variables']:
            return

        iterables = self.current_step['dynamic_variables']['iterables']
        standard = self.current_step['dynamic_variables']['standard']

        if iterables:
            for i in iterables.keys():
                for k, v in iterables[i].items():
                    if type(v) is str:
                        self.current_step[i][k] = self.__current_cache[v][self.__current_icfg[i][k]]
                    else:
                        self.current_step[i][k] = self.__current_icfg[i][k]
        if standard:
            for s in standard.keys():
                if type(standard[s]) is not dict:
                    self.current_step[s] = self.__current_cache[standard[s]]
                    continue

                for k, v in s.items():
                    self.current_step[s][k] = self.__current_cache[v]

    def __list_handler(self, response: list) -> list:
        result = list()
        for elem in response:
            if not self.current_step['output']['key']:
                result.append(elem)
            elif self.current_step['output']['key'] in elem:
                result.append(elem[self.current_step['output']['key']])

        if (self.current_step['output']['is_chain_final']
                and self.current_step['name'] in self.__current_cache):
            self.__current_cache[self.current_step['name']] += result
        else:
            self.__current_cache[self.current_step['name']] = result

        return result

    def __output_handler(self, response: list):
        address = self.current_step['output_path'].split('.')
        output = response

        for sub in address:
            try:
                output = output[sub]
            except (KeyError, TypeError):
                return -1

        return self.__list_handler(response=output) if output else -1

    def __reset_icfg(self):
        """Reset iterator config
        """
        self.__current_icfg = dict()

    def __reset_cache(self):
        """Reset cache
        """
        self.__current_cache = dict()
