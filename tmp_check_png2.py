from PIL import Image
import numpy as np
im=Image.open(r"C:/Users/가산 솔리드옴므/Documents/GitHub/AI-Content-OS/artifacts/fabric_single/fabric_single_20260719-B-f7c153fdfe11.png").convert('RGB')
a=np.array(im)
print('mean',a.mean(axis=(0,1)).astype(int))
print('min',a.min(axis=(0,1)), 'max',a.max(axis=(0,1)))
print('corner',a[0,0],a[10,10],a[-1,-1])
