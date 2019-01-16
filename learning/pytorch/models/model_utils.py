import torch

def dump_shared_params(module):
    # type: (torch.nn.Module) -> Dict[str, object]
    return {
        name: param.data.share_memory_().storage()._share_filename_()
        for (name, param) in module.named_parameters()
    }

def load_shared_params(module, params):
    # type: (torch.nn.Module, Dict[str, object]) -> None

    for (name, param) in module.named_parameters():
        storage = torch.Storage._new_shared_filename(*params[name])
        param.data = torch.Tensor(storage).view(param.data.shape)
