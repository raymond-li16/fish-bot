from player import Player
from game import FishGame
from model import FishDecisionMaker
import constants
import card_utils
from tensorflow.keras import Input
from tensorflow.keras.layers import Dense

class Trainer:
    """
    A runner class to create game instances and train the model(s)
    used by all players
    """
    def __init__(self, model_dict):
        """
        Creates a Trainer class object
        :param model_dict: a dictionary that has player IDs as keys
        and models as values
        """
        self.models = model_dict

    @classmethod
    def clean_trainer(cls, fresh_model):
        """
        Creates a Trainer with the player's models being fresh models
        with a desired architecture
        :param fresh_model: a model object (should be untrained)
        :return: A Trainer object
        """
        model_dict = {ID: fresh_model for ID in range(6)}
        return cls(model_dict)

    def run_and_train_games(self, num_games, train_interval=1):
        """
        Runs some number of games
        Performs a training step after each game
        :param num_games: number of games to train
        :param train_interval: interval to train games
        """
        models = [self.models[i] for i in range(6)]
        for i in range(num_games):
            training_game = FishGame.start_random_game(models)
            training_game.run_whole_game()
            # TODO train
            if i % train_interval == 0:
                already_trained = set([])
                for m in models:
                    if m not in already_trained:
                        m.fit(1)
                        m.check_clean_memory(constants.MAX_HISTORY_LENGTH)
                        already_trained.add(m)

    def get_models(self):
        """
        Gets the models from the players
        :return: A dictionary of models if different players have different
        models
        """
        return self.models

if __name__ == "__main__":
    m = FishDecisionMaker(Input(constants.SIZE_STATES), Dense(constants.SIZE_ACTIONS))
    trainer = Trainer({ID: m for ID in range(6)})
    trainer.run_and_train_games(1000)
