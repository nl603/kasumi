from pys.pytools import tuple_intersection, tuple_minus, tuple_union, tuple_or_object, validate_type
from basics.basictools import dp, DP, Symbol, dp_from_int, as_dp
from basics.domains import ring, Ring, polynomialring, PolynomialRing, Relation
from geometries.geotools import Point
import itertools
import random
import numpy as np

class Poly:
	"""
	represents an element of polynomial ring

	Example:
	>>> x = symbols("x")
	>>> Poly(x**2 - 2*x + 1)
	Poly(x**2 - 2*x + 1, x)
	>>> Poly(x ** 2 - 2*x + 1, mod=3)
	Poly(x**2 - 2*x + 1, x, mod=3)
	>>> from basics.domains import ring
	>>> ff = ring(mod=3, a**2 - 2)
	>>> Poly(x**2 - 2*x + 1, dom=ff)
	Poly(x**2 - 2*x + 1, x, mod=3, rel=a**2 - 2)

	"""

	def __new__(cls, rep, *var, **options):
		if "dom" in options:
			"""
				reduce rep with options["dom"]
			"""
			if isinstance(rep, (DP, Poly, Symbol)):
				if isinstance(rep, DP):
					rep = options["dom"].reduce(rep)
				elif isinstance(rep, Poly):
					rep = rep.reduce()
				else:
					rep = options["dom"].reduce(rep.as_dp())
				if rep.is_constant():
					rep = rep.get_constant()
			var_ = tuple_union(options["dom"].indet_vars, var)
		else:
			var_ = var
		if isinstance(rep, int):
			self = super().__new__(Integer)
		elif isinstance(rep, Symbol):
			if rep in var:
				self = super().__new__(Poly)
			else:
				self = super().__new__(Constant)
		elif isinstance(rep, DP):
			if len(var_) > 0:
				if np.any(np.array(rep.degree(*var_)) > np.array((0,)*len(var_))):
					self = super().__new__(Poly)
				else:
					self = super().__new__(Constant)
			else:
				self = super().__new__(Poly)
		else:
			raise TypeError("rep must be int, Symbol, DP, Poly, Contant or Integer object, not %s" % rep.__class__.__name__)
		return self

	def __init__(self, rep, *var, **options):
		if isinstance(rep, Poly):
			self.rep = rep.rep
			self.indet_vars = rep.indet_vars
			self.const_vars = rep.const_vars
			self.inner_vars = rep.inner_vars
			self.coeff_dom = rep.coeff_dom
			self.dom = rep.dom
		else:
			if isinstance(rep, DP):
				pass
			elif isinstance(rep, int):
				rep = dp_from_int(rep, var)
			elif isinstance(rep, Symbol):
				rep = rep.as_dp()
			else:
				raise TypeError("rep must be Poly or DP, not %s" % rep.__class__.__name__)

			"""

			* Set domain options

			Given "dom" option, initialize with it.
			Not given, construct PolynomialRing object and set to "dom" option

			"""

			if "dom" in options:
				validate_type(options["dom"], PolynomialRing)
				dom = options["dom"]
				self.indet_vars, self.const_vars = self._set_var(rep, tuple_union(dom.indet_vars, var))
				self.inner_vars = tuple_union(self.indet_vars, self.const_vars)
				self.coeff_dom = ring(*self.const_vars, mod=dom.coeff_dom.mod, rel=dom.coeff_dom.rel)
				self.dom = polynomialring(*self.indet_vars, coeff_dom=self.coeff_dom, quo=dom.quo)
			else:
				self.indet_vars, self.const_vars = self._set_var(rep, var)
				self.inner_vars = tuple_union(self.indet_vars, self.const_vars)

				if "coeff_dom" in options:
					validate_type(options["coeff_dom"], Ring)
					self.coeff_dom = options["coeff_dom"]
				else:
					if "mod" in options:
						validate_type(options["mod"], int)
						mod = options["mod"]
					else:
						mod = 0

					if "rel" in options:
						validate_type(options["rel"], int, tuple, DP, Relation)
						rel = options["rel"]
					else:
						rel = 0

					self.coeff_dom = ring(*self.const_vars, mod=mod, rel=rel)
					if len(self.coeff_dom.const_vars) == 0:
						pass
					else:
						self.rep = self.rep.sort_vars(tuple_union(self.inner_vars, self.coeff_dom.const_vars))

				if "quo" in options:
					validate_type(options["rel"], int, tuple, DP, Relation)
					quo = options["rel"]
				else:
					quo = 0

				self.dom = polynomialring(*self.indet_vars, coeff_dom=self.coeff_dom, quo=quo)
			self.rep = self.reduce()

	def _set_var(self, rep, var):
		if len(var) == 0:
			self.rep = rep
			return (rep.inner_vars, tuple())
		else:
			self.rep = rep.sort_vars(tuple_union(var, rep.inner_vars))
			return var, tuple_minus(rep.inner_vars, var)

	def __repr__(self):
		repr_ = "%s(%s, %s" % (self.__class__.__name__, str(self), tuple_or_object(self.indet_vars))
		if self.dom.mod > 0:
			repr_ += ", mod: %s" % self.dom.mod
		if self.dom.rel != 0:
			repr_ += ", rel: %s" % str(self.dom.rel)
		if self.dom.quo != 0:
			repr_ += ", quo: %s" % str(self.dom.quo)
		repr_ += ")"
		return repr_

	def __str__(self):
		return self.as_dist()

	"""
	Binary operators:
	add, sub, mul, floordiv, mod, pow
	"""

	def reduce(self):
		return self.dom.reduce(self.rep)

	def __add__(f, g):
		f_, g_ = _binary_uniform(f, g)
		if f.dom.mod:
			add_ = (f_ + g_) % f.dom.mod
		else:
			add_ = f_ + g_
		return poly(add_, dom=f.dom)

	def __radd__(f, g):
		return f + g

	def __sub__(f, g):
		return f + (- g)

	def __rsub__(f, g):
		return - f + g

	def __mul__(f, g):
		f_, g_ = _binary_uniform(f, g)
		if f.dom.mod:
			mul_ = (f_ * g_) % f.dom.mod
		else:
			mul_ = f_ * g_
		return poly(mul_, dom=f.dom)

	def __rmul__(f, g):
		return f * g

	def __neg__(f):
		return f * (-1)

	def __truediv__(f, g):
		if isinstance(g, int):
			if f.mod > 0:
				return poly(f.rep.div(g, f.dom.mod), dom=f.dom)
			else:
				raise TypeError("can divide only on field")
		else:
			raise TypeError("unsupported operand type(s) for '/'")

	def __floordiv__(f, g):
		if isinstance(g, int):
			if f.mod > 0:
				return poly(f.rep.div(g, f.dom.mod), dom=f.dom)
			else:
				raise TypeError("can divide only on fields")

		"""
		* Validation part
		validate f (and g) is univariate and f has the same indeterminate as g
		"""

		if not f.is_univariate():
			raise TypeError("operands must be univariate polynomial")
		if not f.indet_vars == g.indet_vars:
			raise TypeError("operands must have the same variables")

		if f.degree() < g.degree():
			return poly(0, dom=f.dom)

		"""
		* Calculation part
		"""

		var = f.get_univariate()
		q, r, v = poly(0, *f.indet_vars, dom=f.dom), f, poly(var, *f.indet_vars, dom=f.dom)
		while r.degree(var) >= g.degree(var):
			t = (LC(r) / LC(g)) * v ** (r.degree(var) - g.degree(var))
			r = r - t * g
			q = q + t
		return q

	def __mod__(f, g):
		return f - (f // g) * g

	def __pow__(f, e):
		validate_type(e, int)
		if e < 0:
			raise ValueError("exponent must be positive")
		if e == 0:
			return poly(1, *f.indet_vars, dom=f.dom)
		num_ = bin(e).replace('0b', '')
		pow_ = 1
		for i in num_:
			pow_ = pow_ * pow_
			if i == '1':
				pow_ = f * pow_
		return pow_
		# len_ = len(num_)
		# list_ = [len_ - d - 1 for d in range(len_) if num_[d] == '1']
		# pow_ = 1
		# for l in list_:
		# 	pow_ *= _pow_self(f, l)
		# return pow_

	def __eq__(f, g):
		if isinstance(g, Poly):
			if f.rep == g.rep:
				return True
			else:
				return False
		elif isinstance(g, DP) or isinstance(g, int):
			if f.rep == g:
				return True
			else:
				return False
		elif isinstance(g, Symbol):
			if f.rep == as_dp(g):
				return True
			else:
				return False
		else:
			raise TypeError("unsupported operand type(s) for '=='")
	
	"""
	* Iterable magic methods
	"""

	def __getitem__(self, item):
		return self.rep[item]

	def __setitem__(self, key, value):
		raise NotImplementedError()

	def __iter__(self):
		return iter(self.rep.coeffs)

	def __len__(self):
		return len(self.rep)

	"""
	* Iterator methods
	"""

	def it_dist(self, termorder="lex", with_index=False, zero_skip=True):
		"""
		generate coefficients of each index of exponents,
		return int or DP object with index tuple if with_index is True.
		"""

		validate_type(termorder, str)
		if termorder == "lex":
			iters = [range(self.degree(v, non_negative=True), -1, -1) for v in self.indet_vars]
			for p in itertools.product(*iters):
				c = self.rep[p]
				if zero_skip and c == 0:
					continue
				if with_index:
					yield (p, c)
				else:
					yield c
		elif termorder == "grevlex":
			raise NotImplementedError()
		else:
			raise TypeError("given unsupported termorder '%s'" % termorder)

	def it_reversed_dist(self):
		pass

	"""
	* Reprisentation methods
	"""

	def as_dist(self, termorder="lex", total=False):
		if total:
			return self.rep.as_dist(termorder)
		else:
			rep_, lt, flag_one, flag_paren = str(), True, False, False
			if self.is_zero():
				return "0"
			for data in self.it_dist(termorder=termorder, with_index=True):
				if data[1] == 0:
					continue

				# plus minus part
				if lt:
					lt = False
					if data[1] < 0:
						rep_ += "- "
				else:
					if data[1] > 0:
						rep_ += " + "
					else:
						rep_ += " - "

				# DP bracket part
				if isinstance(data[1], DP):
					if data[1].is_monomial() or not any(data[0]):
						pass
					else:
						flag_paren = True
						rep_ += "("

				# coeffcients part
				if data[1] == 1 or data[1] == -1:
					flag_one = True
				else:
					flag_one = False
					rep_ += str(abs(data[1]))
					if flag_paren:
						flag_paren = False
						rep_ += ")"
					if any(data[0]):
						rep_ += "*"

				# variables part
				for i in range(len(self.indet_vars)):
					if data[0][i] > 1:
						rep_ += str(self.indet_vars[i]) + "**" + str(data[0][i])
					elif data[0][i] == 1:
						rep_ += str(self.indet_vars[i])
					else:
						continue
					if i < len(self.indet_vars) - 1 and any(data[0][(i + 1):]):
						rep_ +="*"

				# last one modification
				if flag_one and not any(data[0]):
					rep_ += "1"

			return rep_

	def as_list(self):
		return self.rep.as_list()

	def as_dp(self):
		return self.rep

	"""
	* Degree methods
	"""

	def degree(self, *var, total=False, as_dict=False, any_vars=False, non_negative=False):
		if total:
			d, i = 0, len(self.indet_vars)
			for v in self.indet_vars:
				d_ = self.rep.degree(v)
				if d_ == -1:
					i -= 1
				else:
					d += d_
			if i == 0:
				if non_negative:
					return 0
				else:
					return -1
			else:
				return d
		else:
			return self.rep.degree(*var, total=total, as_dict=as_dict, any_vars=any_vars, non_negative=non_negative)

	"""
	* Validators
	These functions return bool.
	"""

	def is_univariate(self):
		if len(self.indet_vars) == 1:
			return True
		else:
			if self.degree(*self.indet_vars).count(0) < len(self.indet_vars) - 1:
				return False
			else:
				return True

	def is_zero(self):
		return self.rep.is_zero()

	"""
	* Getting information methods
	"""

	def get_modulus(self):
		return self.dom.mod

	def get_domain(self):
		return self.dom

	def get_variables(self):
		return self.indet_vars

	def get_coeff_dom(self):
		return self.coeff_dom

	def get_univariate(self):
		if self.is_univariate():
			return next(iter(v for v in self.indet_vars if self.degree(v) > 0))
		else:
			raise TypeError("it is not univariate")

	def subs(self, point):
		if isinstance(point, tuple) or isinstance(point, list):
			if len(point) > len(self.indet_vars):
				point_ = list()
				for i in range(len(self.indet_vars)):
					point_.append(point[i])
			elif len(point) == len(self.indet_vars):
				pass
			else:
				point_ = point + (0, )*(len(self.indet_vars) - len(point))
			point_dict = dict(zip(self.indet_vars, point_))
		elif isinstance(point, dict):
			if set(self.indet_vars) == set(point):
				pass
			else:
				for v in self.indet_vars:
					if v in point:
						pass
					else:
						point[v] = 0
				for v in tuple_minus(tuple(point.keys()), self.indet_vars):
					point.pop(v)
			point_dict = point
		elif isinstance(point, Point):
			point_dict = point.as_dict()
		else:
			raise TypeError("point must be tuple, dict or Point, not '%s'" % point.__class__.__name__)
		return poly(self.rep.subs(point_dict), dom=self.dom)

	def random_poly(self, *var, deg=1):

		"""
			* random_poly()
			return a random polynomial of which domain is the same as of self.

		"""
		return poly(self.dom.random(*var, deg=deg), dom=self.dom)

	def get_monic(self):
		if self.coeff_dom.is_field:
			return LC(self).inverse() * self
		else:
			raise TypeError("cannot make monic")

	def set_monic(self):
		self.rep = self.get_monic().rep

def poly(f, *var, **options):
	return Poly(f, *var, **options)

def _binary_uniform(f, g):
	if isinstance(g, int) or isinstance(g, DP) or isinstance(g, Symbol):
		f_, g_ = f.rep, as_dp(g, *f.indet_vars)
	elif isinstance(g, Poly):
		f_, g_ = f.rep, g.rep
	else:
		raise TypeError("unsupported operand type(s) for '+'")
	return f_, g_

def _pow_self(f, e):
	for i in range(e):
		f = f * f
	return f

class Constant(Poly):
	"""
	* Binary operations
	"""

	def __truediv__(f, g):
		if not f.coeff_dom.is_field:
			raise TypeError("cannot divide not on field")
		if isinstance(g, Constant):
			return f * g ** (f.coeff_dom.number() - 2)
		elif isinstance(g, int):
			return f / g

	def __floordiv__(f, g):
		pass

	def inverse(f):
		return f ** (f.coeff_dom.number() - 2)

	"""
	* Validators
	These functions return bool.
	"""

	def is_univariate(self):
		if super().is_univariate():
			return True
		else:
			if len(self.const_vars) == 1:
				return True
			else:
				return False

	"""
	* Degree methods
	"""

	def degree(self, *var, total=False, as_dict=False, any_vars=False, non_negative=False):
		return 0

	def subs(self, point):
		raise TypeError("cannot substitute points to %s" % self.__class__.__name__)

class Integer(Constant):

	"""
	* Validators
	These functions return bool.
	"""

	def is_univariate(self):
		return True

	"""
	* Degree methods
	"""

	def degree(self, *var, total=False, as_dict=False, any_vars=False, non_negative=False):
		if non_negative:
			return 0
		else:
			if self.rep == 0:
				return -1
			else:
				return 0

"""
* Poly functions
First argument must be Poly object
"""

def diff(f, *var):
	validate_type(f, Poly)
	if len(var) > 1:
		raise ValueError("the number of variable argument must be 0 or 1, not %s" % str(len(var)))
	elif len(var) == 1:
		var_ = var[0]
		sorted_vars = tuple_union(var, tuple_minus(f.inner_vars, var))
		rep_ = f.rep.sort_vars(sorted_vars)
	else:
		var_ = f.indet_vars[0]
		rep_ = f.rep

	return poly(rep_.diff(var_), *f.indet_vars, dom=f.dom)

def solve(f, *var, extend=False, as_poly=False):
	solution_ = list()
	if len(var) == 0:
		var_ = f.indet_vars
	else:
		var_ = var
	if extend:
		pass
	else:
		for p in f.coeff_dom.it_points(*var_):
			if f.subs(p) == 0:
				if as_poly:
					solution_.append(poly(p, *f.indet_vars, dom=f.dom))
				else:
					solution_.append(p)
	return solution_

def uni_solve(f, infinite=False, as_poly=False):
	if len(f.indet_vars) > 1:
		try:
			var = f.get_univariate()
		except TypeError:
			raise TypeError("argument must be univariate polynomial")
	elif len(f.indet_vars) == 1:
		var = f.indet_vars[0]
	else:
		raise TypeError("argument must be univariate polynomial")
	if not infinite and not f.coeff_dom.is_finite:
		raise TypeError("set True the option 'infinite' if solve polynomials over inifinite domain")
	solution_, d, e = list(), f.degree(var), f.coeff_dom.mod
	for p in f.coeff_dom.it_elements():
		if f.subs({var: p}) == 0:
			p = poly(p, *f.indet_vars, dom=f.dom)
			for i in range(d):
				if as_poly:
					solution_.append({var: p ** (e ** i)})
				else:
					solution_.append({var: (p ** (e ** i)).as_dp()})
			break
	return solution_

def LC(f, termorder="lex"):
	validate_type(f, Poly)
	lc_ = next(f.it_dist(zero_skip=False))
	return poly(lc_, *f.indet_vars, dom=f.dom)

def LM(f, termorder="lex"):
	pass

def LT(f, termorder="lex"):
	pass

def gcd(f, g):
	validate_type(f, Poly)
	validate_type(g, Poly)
	if not f.is_univariate() or not g.is_univariate():
		raise TypeError("arguments must be univariate polynomials")
	if f.degree() < g.degree():
		f, g = g, f
	q = f % g
	if q == 0:
		return g
	else:
		return gcd(g, q).get_monic()

def factor(f, deg=0):
	validate_type(f, Poly)
	validate_type(deg, int)
	if deg == 0:
		"""
			calculate with Cantor-Zassenhaus algorithm
		"""
		pass
	else:
		if not f.is_univariate():
			raise ValueError("f must be a univatiate polynomial")
		var = f.get_univariate()
		r, q = f.degree(var) // deg, f.coeff_dom.number()
		dom_ = f.dom.add_quotient(f.rep)
		F = [f]
		while len(F) < r:
			g = poly(f.dom.random(deg=r*deg-1, monic=True), dom=dom_)
			g = g ** ((q ** deg - 1) // 2) - 1
			g = poly(g.rep, *f.indet_vars, dom=f.dom)
			if g == 0:
				continue
			F_1 = list()
			while len(F) > 0:
				h = F.pop()
				if h.degree(var) <= deg:
					continue
				z = gcd(h, g)
				if z == 1 or z == h:
					F_1.append(h)
				else:
					F_1.append(z)
					F_1.append(h // z)
			F = F_1
		return F