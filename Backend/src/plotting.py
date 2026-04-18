import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import statistics
import os, torch
import numpy as np
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

try:
    import scienceplots
    plt.style.use(['science', 'ieee'])
except Exception:
    plt.style.use('seaborn-v0_8-darkgrid')

import matplotlib as mpl
mpl.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams["text.usetex"] = False
plt.rcParams['figure.figsize'] = 6, 2

os.makedirs('plots', exist_ok=True)

def smooth(y, box_pts=1):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth

def plotter(name, y_true, y_pred, ascore, labels):
	if 'TranAD' in name: y_true = torch.roll(y_true, 1, 0)
	os.makedirs(os.path.join('plots', name), exist_ok=True)
	pdf = PdfPages(f'plots/{name}/output.pdf')
	labels_dim = labels.shape[1] if labels.ndim > 1 else 1
	for dim in range(y_true.shape[1]):
		y_t, y_p, a_s = y_true[:, dim], y_pred[:, dim], ascore[:, dim]
		# Convert tensors to numpy arrays on CPU if they're on CUDA
		y_t = y_t.cpu().numpy() if torch.is_tensor(y_t) else y_t
		y_p = y_p.cpu().numpy() if torch.is_tensor(y_p) else y_p
		a_s = a_s.cpu().numpy() if torch.is_tensor(a_s) else a_s
		# Use the same dimension for labels if available, otherwise use the first one
		l = labels[:, dim] if labels.ndim > 1 and dim < labels_dim else (labels[:, 0] if labels.ndim > 1 else labels)
		l = l.cpu().numpy() if torch.is_tensor(l) else l
		fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
		ax1.set_ylabel('Value')
		ax1.set_title(f'Dimension = {dim}')
		# if dim == 0: np.save(f'true{dim}.npy', y_t); np.save(f'pred{dim}.npy', y_p); np.save(f'ascore{dim}.npy', a_s)
		ax1.plot(smooth(y_t), linewidth=0.2, label='True')
		ax1.plot(smooth(y_p), '-', alpha=0.6, linewidth=0.3, label='Predicted')
		ax3 = ax1.twinx()
		ax3.plot(l, '--', linewidth=0.3, alpha=0.5)
		ax3.fill_between(np.arange(l.shape[0]), l, color='blue', alpha=0.3)
		if dim == 0: ax1.legend(ncol=2, bbox_to_anchor=(0.6, 1.02))
		ax2.plot(smooth(a_s), linewidth=0.2, color='g')
		ax2.set_xlabel('Timestamp')
		ax2.set_ylabel('Anomaly Score')
		pdf.savefig(fig)
		plt.close()
	pdf.close()
