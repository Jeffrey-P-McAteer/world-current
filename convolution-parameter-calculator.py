# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "toml",
#   "diskcache",
#   "platformdirs",
#   "staticmap",
#   "Pillow",
#   "shapely",
#   "requests",
#   "numpy",
#   "torch",
#   "torchvision",
# ]
# ///

import os
import sys

features_img_path = sys.argv[1]
goal_img_path = sys.argv[2]

import torch
import torch.nn.functional as F
from torchvision import transforms
from torchvision.utils import save_image
from PIL import Image
import numpy as np
import os

# Config
KERNEL_SIZE = 9
NUM_KERNELS = 500
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# Load and preprocess images
def load_image(path):
    image = Image.open(path).convert('L')  # Convert to grayscale
    transform = transforms.Compose([
        transforms.ToTensor(),  # Converts to shape [1, H, W], values in [0, 1]
    ])
    return transform(image).to(DEVICE)

# Convolve image with a 9x9 kernel
def apply_kernel(image, kernel):
    kernel = kernel.view(1, 1, KERNEL_SIZE, KERNEL_SIZE)
    return F.conv2d(image.unsqueeze(0), kernel, padding=KERNEL_SIZE // 2)

# Evaluation metric: MSE loss
def loss_fn(predicted, target):
    return F.mse_loss(predicted, target)

# Find the best kernel from random ones
def find_best_kernel(image_input, image_target, num_kernels):
    best_loss = float('inf')
    best_kernel = None

    for i in range(num_kernels):
        kernel = torch.randn(KERNEL_SIZE, KERNEL_SIZE, device=DEVICE, requires_grad=False)
        kernel = kernel / kernel.abs().sum()  # Normalize kernel

        output = apply_kernel(image_input, kernel)
        loss = loss_fn(output, image_target)

        if loss < best_loss:
            best_loss = loss.item()
            best_kernel = kernel.detach().cpu()

        print(f'Finished kernel {i}/{num_kernels}')

    return best_kernel, best_loss

# === Main ===
def main():
    # Replace with your image paths
    path_input = features_img_path
    path_target = goal_img_path

    if not os.path.exists(path_input) or not os.path.exists(path_target):
        print("Please place 'input.png' and 'target.png' in the current directory.")
        return

    image_input = load_image(path_input)
    image_target = load_image(path_target)
    image_target = image_target.unsqueeze(0)  # shape becomes [1, 1, H, W]

    print("Finding best kernel...")
    best_kernel, best_loss = find_best_kernel(image_input, image_target, NUM_KERNELS)

    print("Best kernel (9x9):")
    print(best_kernel.numpy())
    print(f"Loss: {best_loss:.6f}")

    # Write best output to /tmp/out.png
    out_file_path = '/tmp/out.png'
    best_output = apply_kernel(image_input, best_kernel).squeeze(0).detach().cpu() # shape: [H, W]
    # Normalize for saving (min-max normalization to [0, 1])
    output_min, output_max = best_output.min(), best_output.max()
    normalized_output = (best_output - output_min) / (output_max - output_min + 1e-8)

    save_image(normalized_output.unsqueeze(0), "/tmp/out.png")


if __name__ == "__main__":
    main()












