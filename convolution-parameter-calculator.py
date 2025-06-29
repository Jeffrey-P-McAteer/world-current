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
#   "matplotlib",
#   "opencv-python",
# ]
# ///

import os
import sys

features_img_path = sys.argv[1]
goal_img_path = sys.argv[2]

import torch
import torch.nn.functional as F
import cv2
import numpy as np
import matplotlib.pyplot as plt

def load_grayscale_tensor(path, device):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
    tensor = torch.from_numpy(img).unsqueeze(0).unsqueeze(0)  # shape: (1, 1, H, W)
    return tensor.to(device)

def optimize_kernel(image, target, kernel_size=5, iterations=200, lr=0.1):
    device = image.device

    # Initialize kernel as a trainable parameter
    kernel = torch.randn((1, 1, kernel_size, kernel_size), device=device, requires_grad=True)

    optimizer = torch.optim.Adam([kernel], lr=lr)

    for it in range(iterations):
        optimizer.zero_grad()
        output = F.conv2d(image, kernel, padding=kernel_size // 2)
        loss = F.mse_loss(output, target)
        loss.backward()
        optimizer.step()

        if it % 10 == 0:
            print(f"Iteration {it}/{iterations}, Loss: {loss.item():.6f}")

    return kernel.detach().cpu().squeeze().numpy(), output.detach().cpu().squeeze().numpy()

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    image_path = features_img_path
    mask_path = goal_img_path

    image = load_grayscale_tensor(image_path, device)
    mask = load_grayscale_tensor(mask_path, device)

    # Ensure mask is binary
    mask = (mask > 0.5).float()

    kernel, output = optimize_kernel(
        image, mask,
        kernel_size=5,
        iterations=25000,
        lr=0.01
    )

    # Display results
    image_np = image.cpu().squeeze().numpy()
    mask_np = mask.cpu().squeeze().numpy()

    plt.figure(figsize=(12, 4))
    plt.subplot(1, 3, 1)
    plt.title('Original')
    plt.imshow(image_np, cmap='gray')
    plt.axis('off')

    plt.subplot(1, 3, 2)
    plt.title('Target Mask')
    plt.imshow(mask_np, cmap='gray')
    plt.axis('off')

    plt.subplot(1, 3, 3)
    plt.title('Convolved Output')
    plt.imshow(output, cmap='gray')
    plt.axis('off')

    plt.tight_layout()
    plt.savefig("/tmp/result.png", dpi=400)

    print("Learned Kernel:")
    print(kernel)
    with open('/tmp/result.txt', 'w') as fd:
        fd.write(f'Learned Kernel:\n{kernel}\n')

    print(f'See /tmp/result.png and /tmp/result.txt')


if __name__ == '__main__':
    main()






