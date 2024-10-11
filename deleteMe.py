import torch

model_data = torch.load('/home/ithemal/ithemal/learning/pytorch/saved/my_experiment/2024-08-31/trained.mdl')
print(type(model_data))

if isinstance(model_data, dict):
    print(model_data.keys())
else:
    print(model_data)
