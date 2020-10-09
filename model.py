import numpy as np
from tensorflow import keras
from tensorflow.keras import layers
import card_utils
import constants


class FishDecisionMaker(keras.Sequential):
    """
    A decision maker for the player class for Fish.
    This class is a neural network that takes in the game state and
    predicts which player to ask and which card to ask for
    This class is a shared model between all 6 bots in the virtual fish game
    They all use the same logic and train together (not sure if that's a good idea)

    Also note that this model only predicts what cards to ask,
    not when to call.
    When to call is hardcoded (It is when the players know excactly a half suit)

    This model trains on data collected from virtual games

    Game state and action history are stored in the following manner:
    For each player p in the model's applicable players parameter:
    store a list of histories
    Ex) self.state_history[Player 0] =
    [history of game 1, history of game 2, etc.]
    Each history will only contain states and actions that pertain to
    the times when the player takes an action
    Ex) for player 0, history of game 1 will be in the following format:
    State history:
    [
    (state initial, state final) of first action,
    (state initial, state final) of second action,
    etc.
    ]
    Action history:
    [
    (action 1),
    (action 2),
    (action 3) etc.
    ]
    Rewards history:
    [
    (rewards 1),
    (rewards 2),
    ...
    (rewards of game end)
    ]
    All histories will have the same length for a given game.
    """

    def __init__(self, *layers, applicable_players=(), **compile_options):
        """
        Creates the neural network with an architecture given by layers
        :param *layers: A sequential list of Layer Objects defined in keras (ex. InputLayer)
        :param applicable_players: a list of the players that this model is used in
        :param **options: A list of compile options used to compile the network
        """
        super().__init__()
        for l in layers:
            self.add(l)
        self.compile(**compile_options)
        self.applicable_players = applicable_players
        self.action_history = {p: [] for p in applicable_players}
        self.state_history = {p: [] for p in applicable_players}
        self.rewards_history = {p: [] for p in applicable_players}

    def update_data(self, player, info_i, hs_info_i, num_cards_i, public_info_i, public_hs_info_i,
                    info_f, hs_info_f, num_cards_f, public_info_f, public_hs_info_f,
                    ID_ask, ID_target, card, success, game_result):
        """
        Updates the history lists of the model, given a transaction and state
        All params with *_i are initial state, *_f means final state
        :param player: the player that is reporting the data update
        :param info_i: defined in Player class
        :param hs_info_i: defined in Player class
        :param num_cards_i: defined in Player class
        :param public_info_i: defined in Player class
        :param public_hs_info_i: defined in Player class
        :param info_f: defined in Player class
        :param hs_info_f: defined in Player class
        :param num_cards_f: defined in Player class
        :param public_info_f: defined in Player class
        :param public_hs_info_f: defined in Player class
        :param ID_ask: ID of asker
        :param ID_target: ID of target
        :param card: Card being asked for
        :param success: Was the ask successful
        :param game_result: 0 if still ongoing, 1 if won, -1 if lost
        """
        state_i = self.generate_state_vector(info_i, hs_info_i, num_cards_i, public_info_i,
                                             public_hs_info_i, player, game_result)
        state_f = self.generate_state_vector(info_f, hs_info_f, num_cards_f, public_info_f,
                                             public_hs_info_f, player, game_result)
        self.state_history[player][-1].append((state_i, state_f))
        self.action_history[player][-1].append(self.generate_action_number(ID_ask, ID_target, card))
        self.rewards_history[player][-1].append(self.generate_reward_ask(success))

    def create_new_histories(self, num_histories):
        """
        This method is intended to be used at the start of a new game
        It creates num_histories new arrays in the histories
        (action, state, rewards, done) to log games
        """
        for i in range(num_histories):
            for p in self.applicable_players:
                self.action_history[p].append([])
                self.state_history[p].append([])
                self.rewards_history[p].append([])

    @staticmethod
    def generate_state_vector(info, hs_info, num_cards, public_info, public_hs_info, ID_player, game_result):
        """
        Generates a state vector from the player's information

        The structure of the state vector is as follows:
        Length: 762 (SIZE_STATES)
        The order of players in each section starts with the ID of the player
        and counts up mod 6 (example: 3, 4, 5, 0, 1, 2)
        The order of cards is defined in card_utils.gen_all_cards
        The first 54 * 6 = 324 entries are for the info dict, with the values
        being the same as in the info dict
        The next 54 * 6 = 324 entries are for the public_info dict, with the values
        being the same as in the public_info dict
        The next 9 * 6 = 54 entries are for the hs_info, with the values
        being the same as in the hs_info dict
        The last 6 entries are the number of cards each player has

        :param info: defined in Player class
        :param hs_info: defined in Player class
        :param num_cards: defined in Player class
        :param public_info: defined in Player class
        :param public_hs_info: defined in Player class
        :param ID_player: ID of the player
        :param game_result: 0 if not determined, 1 if win, -1 if loss
        :return: a state vector
        """
        player_order = list(range(6))[ID_player:] + list(range(6))[:ID_player]
        state = []
        # Info dict
        for ID in player_order:
            for card in card_utils.gen_all_cards():
                state.append(info[ID][card])
        # Public Info dict
        for ID in player_order:
            for card in card_utils.gen_all_cards():
                state.append(public_info[ID][card])
        # Half suit info dict
        for ID in player_order:
            for hs in card_utils.gen_all_halfsuits():
                state.append(hs_info[ID][hs])
        # Public half suit info dict
        for ID in player_order:
            for hs in card_utils.gen_all_halfsuits():
                state.append(public_hs_info[ID][hs])
        # Num cards
        for ID in player_order:
            state.append(num_cards[ID])
        # Game result
        state.append(game_result)
        return state

    @staticmethod
    def generate_action_number(ID_ask, ID_target, card):
        """
        Generates an action vector from the player's action
        This vector is universal to all players, meaning it is independent of player ID
        For example, player 0 asking player 3 for a Jc will return the ]
        same vector as player 1 asking player 4 for a Jc
        This is to ensure that the model can be used universally among all players
        :param ID_ask: ID of player asking
        :param ID_target: ID of target
        :param card: Card being asked
        :return: Action number (0-161)
        """
        player_num = (((ID_target - ID_ask) % 6) - 1) // 2
        card_num = list(card_utils.gen_all_cards()).index(card)
        return player_num * constants.DECK_SIZE + card_num

    @staticmethod
    def generate_reward_ask(success):
        """
        Generates a reward based on whether the ask was a success
        :param success:
        :return: reward
        """
        if success:
            return constants.REWARD_SUCCESSFUL_ASK
        return constants.REWARD_UNSUCCESSFUL_ASK

    def update_game_done(self, player, win):
        """
        Changes the rewards in the final state (right before the game ends) to win or lose

        Also creates a new game done state
        :param player: the player that is being updated
        :param win: true if player won
        """
        if win:
            # Set the last game's last reward to win
            self.rewards_history[player][-1][-1] = constants.REWARD_WIN
            # Set the last entry of the last state vector's final to win
            self.state_history[player][-1][-1][1][-1] = 1
        else:
            # Set the last game's last reward to lose
            self.rewards_history[-1] = constants.REWARD_LOSE
            # Set the last entry of the last state vector's final to lose
            self.state_history[player][-1][-1][1][-1] = -1

    def fit_n_games(self, history_length,
                    batch_size=None,
                    epochs=1,
                    verbose=1,
                    callbacks=None,
                    validation_split=0.,
                    validation_data=None,
                    shuffle=True,
                    class_weight=None,
                    sample_weight=None,
                    initial_epoch=0,
                    steps_per_epoch=None,
                    validation_steps=None,
                    validation_batch_size=None,
                    validation_freq=1,
                    max_queue_size=10,
                    workers=1,
                    use_multiprocessing=False):
        """
        Fits the model with q learning y values and states for x values
        :param history_length: maximum number of games to fit history on
        Other parameters are inherited from superclass
        """
        start = len(self.done_history) - 1
        count = 0
        while start > 0 and count < history_length + 1:
            if self.done_history[start]:
                count += 1
            start -= 1
        if start > 0:
            start += 1
        x, y = [], []
        for i in range(start, len(self.done_history)):
            if not self.done_history[i]:
                x.append(self.state_history[i])
                print("start: {}  current: {}   finish: {}".format(start, i, len(self.done_history) - 1))
                next_state = np.array(self.state_history[i + 1]).reshape(1, constants.SIZE_STATES)
                target = self.rewards_history[i] + constants.GAMMA * np.max(self.predict(next_state))
                y0 = self.predict(np.array(self.state_history[i]).reshape(1, constants.SIZE_STATES))[0]
                y0[self.action_history[i]] = target
                y.append(y0)

        x = np.array(x)
        y = np.array(y)
        self.fit(x, y, batch_size, epochs, verbose, callbacks, validation_split,
                 validation_data, shuffle, class_weight, sample_weight, initial_epoch,
                 steps_per_epoch, validation_steps, validation_batch_size, validation_freq,
                 max_queue_size, workers, use_multiprocessing)

    def check_clean_memory(self, length):
        """
        if length of history is longer than length, delete the first
        n games until the history is shorter than length
        :return: True if history was deleted, else False
        """
        if len(self.done_history) > length:
            start = len(self.done_history) - length
            while not self.done_history[start]:
                start += 1
            self.state_history = self.state_history[start:]
            self.action_history = self.action_history[start:]
            self.rewards_history = self.action_history[start:]
            self.done_history = self.done_history[start:]
            return True
        return False
