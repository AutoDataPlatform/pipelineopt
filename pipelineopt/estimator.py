import os

import numpy as np

from sklearn.metrics import accuracy_score

import sklearn
from sklearn import *

from sklearn.utils import shuffle
from sklearn.pipeline import make_pipeline

from grammaropt.random import RandomWalker
from grammaropt.grammar import as_str
from grammaropt.grammar import build_grammar

filename = os.path.join(os.path.dirname(__file__), 'classifier_grammar')
classifier_grammar = build_grammar(open(filename, 'r').read())

MAX_DEPTH = 3

class Classifier:
    """
    Automatic pipeline optimizer for scikit-learn classifiers.

    Parameters
    ==========

    nb_iter : int
        number of iterations of pipeline optimization.
        each iteration, one full pipeline is evaluated.

    score : function (default is `accuracy`)
        metric to use for evaluation. see `sklearn.metrics`.
        WARNING : the higher the score, the better.

    walker : Walker, the grammar walker to use. Walkers are used to generate pipelines
             from the grammar. the default Walker is RandomWalker and it chooses randomly
             uniformly a pipeline from the grammar defined in `classifier_grammar`.

    valid_ratio : float
        ratio of validation set to use for evaluating the pipelines.
        If valid_ratio is 0, validation is done using the full training set (`X` and `y` in fit),
        except if `X_valid` and `y_valid` are provided in `fit`.

    random_state : int

    Attributes
    ==========

    estimators_ : list of scikit-learn pipelines
        list of all estimators evaluated in the optimization

    scores_ : list of float
        list of estimators scores

    codes_ : list of str
        list of pipelines codes

    best_score_ : float
        best score found

    best_estimator_ : scikit-learn pipeline
        best estimator found

    best_estimator_code_ : str
        best estimator code
    """
    def __init__(self, nb_iter=1, score=accuracy_score, 
                 walker=RandomWalker(classifier_grammar, max_depth=MAX_DEPTH), 
                 valid_ratio=0, random_state=42, verbose=0):
        self.nb_iter = nb_iter
        self.score = score
        self.walker = walker
        self.valid_ratio = valid_ratio
        self.random_state = random_state
        self.estimators_ = []
        self.scores_ = []
        self.codes_ = []
        self.best_score_ = None
        self.best_estimator_ = None
        self.best_estimator_code_ = None
        self.verbose = verbose

    def fit(self, X, y, X_valid=None, y_valid=None):
        if X_valid is None and y_valid is None:
            if self.valid_ratio > 0:
                X, y = shuffle(X, y, random_state=self.random_state)
                nb_train = len(X) - int(len(X) * self.valid_ratio)
                X_train = X[0:nb_train]
                y_train = y[0:nb_train]
                X_valid = X[nb_train:]
                y_valid = y[nb_train:]
            else:
                X_train = X
                y_train = y
                X_valid = X
                y_valid = y
        else:
            X_train = X
            y_train = y

        assert X_valid is not None and y_valid is not None

        wl = self.walker
        for i in range(self.nb_iter):
            wl.walk()
            code = as_str(wl.terminals)
            clf = eval(code)
            try:
                clf.fit(X_train, y_train)
            except Exception as ex:
                if self.verbose:
                    print('Exception on iteration {}, while training "{}". Ignore.'.format(i, code))
                    print(str(ex))
                continue
            score = self.score(y_valid, clf.predict(X_valid))
            if self.verbose:
                print('Iteration {}'.format(i))
                print('Trained "{}"'.format(code))
                print('Score : {}'.format(score))
            self.codes_.append(code)
            self.estimators_.append(clf)
            self.scores_.append(score)
        
        if len(self.scores_):
            idx = np.argmax(self.scores_)
            self.best_score_ = self.scores_[idx]
            self.best_estimator_ = self.estimators_[idx]
            self.best_estimator_code_ = self.codes_[idx]
            if self.verbose:
                print('Best score : {}'.format(self.best_score_))
                print(self.best_estimator_code_)
        return self
    
    def predict(self, X):
        return self.best_estimator_.predict(X)

    def predict_proba(self, X):
        return self.best_estimator_.predict_proba(X)
