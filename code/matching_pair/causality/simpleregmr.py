# Purpose: use mapreduce the calculate each (b0, b1) pair 
#          of the six index
# command: python3 thisfile --jobconf mapreduce.job.reduces=1 inputfile
# Input: ../../../data/fixed_effect.csv

from mrjob.job import MRJob
from mrjob.step import MRStep
import csv


class MRpairreg(MRJob):


	def clean_output(self, row):

		label, x1 = row[0].split(('\t['))
		x1 = float(x1)
		y1 = float(row[1].strip(' '))
		x2 = float(row[2].strip(' '))
		y2 = float(row[3].strip(' ]'))

		return label, (x1, y1, x2, y2)


	def mapper(self, _, line):
		
		row = next(csv.reader([line])) 
		key, val = self.clean_output(row)
		x_diff = val[0] - val[2]
		y_diff = val[1] - val[3]
		rv = (x_diff, y_diff)

		yield key, rv


	def reducer_first_init(self):

		self.count = [0] * 6
		self.x_sum = [0] * 6
		self.y_sum = [0] * 6
		self.convert = {'weather_st_ind':0, 'weather_end_ind':1, 'loc_ind':2, 
						'weekday_ind':3, 'hour_ind':4, 'month_ind': 5}
		self.data_dict = {}
		self.x_mean = [0] * 6
		self.y_mean = [0] * 6


	def reducer_first(self, key, vals):
		
		index = self.convert[key]
		for val in vals:
			x_diff, y_diff = val
			self.x_sum[index] += x_diff
			self.y_sum[index] += y_diff
			self.count[index] += 1


			if index not in self.data_dict:
				self.data_dict[index] = []
			self.data_dict[index].append((x_diff, y_diff))
			

	def reducer_first_final(self):

		self.x_mean = [a/b for a, b in zip(self.x_sum, self.count)]
		self.y_mean = [a/b for a, b in zip(self.y_sum, self.count)]
		

		for key, values in self.data_dict.items():
			for value in values:
				x_diff, y_diff = value
				sxy = (x_diff - self.x_mean[key]) * (y_diff - self.y_mean[key])
				sxx = (x_diff - self.x_mean[key]) ** 2
				value = (sxy, sxx)
				yield key, value

		yield 'parameter', (self.x_mean, self.y_mean, self.count)


	def reducer_second_init(self):

		self.sxx = [0] * 6
		self.sxy = [0] * 6
		self.beta_1 = [0] * 6
		self.beta_0 = [0] * 6
		self.x_mean = [0] * 6
		self.y_mean = [0] * 6
		self.count = [0] * 6
		

	def reducer_second(self, index, vals):

		if index == 'parameter':
			for val in vals:
				self.x_mean, self.y_mean, self.count = val
		else:
			for val in vals:
				sxy, sxx = val
				self.sxy[index] += sxy
				self.sxx[index] += sxx

				
	def reducer_second_final(self):

		self.beta_1 = [a/b for a, b in zip(self.sxy, self.sxx)]
		self.beta_0 = [a - b * c for a, b, c in zip(self.y_mean, self.x_mean, self.beta_1)]
	
		for i in range(6):
			yield  'beta_0', self.beta_0[i]
			yield  'beta_1', self.beta_1[i]


	def steps(self):

		return [MRStep(mapper = self.mapper, 
					   reducer_init = self.reducer_first_init,
					   reducer = self.reducer_first,
					   reducer_final = self.reducer_first_final),

				MRStep(reducer_init = self.reducer_second_init,
					   reducer = self.reducer_second,
					   reducer_final = self.reducer_second_final)]


if __name__ == '__main__':
	MRpairreg.run()
