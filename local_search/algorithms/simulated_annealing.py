import random
from typing import Union
from local_search.algorithms import SubscribableAlgorithm, AlgorithmConfig
from local_search.problems.base.state import State
from local_search.problems.base.problem import Problem
import random
from dataclasses import dataclass
import mpmath
from enum import IntEnum, auto


class SAEscapeStrategy(IntEnum):
    RandomRestart = 0
    Perturbation = auto()
    Reheat = auto()


@dataclass
class SimulatedAnnealingConfig(AlgorithmConfig):
    initial_temperature: int = 5
    cooling_step: float = 0.999
    min_temperature: float = 1e-10
    escape_random_restart_probability: float = 0.33
    escape_perturbation_probability: float = 0.33
    escape_perturbation_size: int = 50
    escape_reheat_probability: float = 0.33
    escape_reheat_ratio: float = 0.1


DEFAULT_CONFIG = SimulatedAnnealingConfig()


class SimulatedAnnealing(SubscribableAlgorithm):
    """
    Implementation of the simulated annealing algorithm.

    A version of stochastic hill climbing, that allows going downhills. 
    """

    def __init__(self, config: SimulatedAnnealingConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.temperature = self.config.initial_temperature
        self._local_optimum_escapes = 0
        self._escape_strategies = list(SAEscapeStrategy)
        self._escape_probabilities = [0 for _ in self._escape_strategies]
        self._escape_probabilities[SAEscapeStrategy.RandomRestart.value] = self.config.escape_random_restart_probability
        self._escape_probabilities[SAEscapeStrategy.Perturbation.value] = self.config.escape_perturbation_probability
        self._escape_probabilities[SAEscapeStrategy.Reheat.value] = self.config.escape_reheat_probability
        self.cooling_time = 0
        super().__init__(config=config)

    def _find_next_state(self, model: Problem, state: State) -> Union[State, None]:
        neighbour = next(self._get_random_neighbours(model, state))
        if model.improvement(neighbour, state) > 0:
            state = neighbour
        else:
            probability = self._calculate_transition_probability(model, state, neighbour)
            if probability >= random.random():
                state = neighbour
        self._update_temperature()

        return state

    def _calculate_transition_probability(self, model: Problem, old_state: State, new_state: State) -> float:
        return mpmath.exp(model.improvement(old_state, new_state) / self.temperature)

    def _update_temperature(self):
        new_temperature = self.temperature * (self.config.cooling_step**self.cooling_time)
        self.cooling_time += 1
        if new_temperature < self.config.min_temperature:
            new_temperature = self.config.min_temperature
        self.temperature = new_temperature

    def escape_local_optimum(self, model: Problem, state: State, best_state: State) -> Union[State, None]:
        self._local_optimum_escapes += 1
        if self._local_optimum_escapes > self.config.local_optimum_escapes_max >= 0:
            return None

        strategy = random.choices(
            self._escape_strategies, weights=self._escape_probabilities)[0]

        if strategy == SAEscapeStrategy.RandomRestart:
            return self._random_restart(model)
        if strategy == SAEscapeStrategy.Perturbation:
            return self._perturb(model, self.config.escape_perturbation_size)
        if strategy == SAEscapeStrategy.Reheat:
            return self._reheat(state)

    def _reheat(self, from_state: State):
        self.temperature = self.config.escape_reheat_ratio * self.config.initial_temperature
        self.cooling_time = 0
        self.steps_from_last_state_update = 0
        return from_state
