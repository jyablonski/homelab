# Hardware

K3s Cluster can run on 3 Beelinks. These are compact PCs with decent CPU & Memory and onboard storage, with an extra M.2 slot for additional storage capacity.

- 1 runs the Control Plane & acts as the Master Node
- 2 run as dedicated worker nodes
- The Master node can also run workloads, which is probably the way to go here if the hardware is powerful enough.
- K3s is lightweight and with only 3 nodes, it's not that worth it to run a dedicated master node just yet.
- Just ensure the master node has some reserved resources on it so it can continue its control plane responsibilities unaffected.
- Can also set all 3 nodes to be masters for full HA, but this is a bit complex and likely unnecessary to start with.

## Rack

The Beelinks have to be physically stored somewhere. This is often done in network racks, where they can be stored close enough together along with room for expansion (storage nodes, UPS backup etc).

Racks have this nomenclature of `U` which is standardized measurement for rack-mounted equipment.

- 1U = 1.75 inches (44.45mm) of vertical height
- Racks are measured by total height: 12U, 24U, 42U, etc.
- 12U Rack is appropriate for a home lab of this size

```text
┌─────────────────────────┐
│  [12U Wall-Mount Rack]  │
├─────────────────────────┤
│ 1U: Home Router         │ <-- Your existing WiFi router
├─────────────────────────┤
│ 1U: MikroTik Switch     │ <-- Network switch
├─────────────────────────┤
│ 1U: Shelf + Beelink 1   │ <-- Node 1 (control plane)
├─────────────────────────┤
│ 1U: Shelf + Beelink 2   │ <-- Node 2 (worker)
├─────────────────────────┤
│ 1U: Shelf + Beelink 3   │ <-- Node 3 (worker)
├─────────────────────────┤
│ 2U: UPS (Battery)       │ <-- Power backup
├─────────────────────────┤
│ Empty space (5U left)   │ <-- Future: NAS, more nodes
│                         │
│                         │
│                         │
│                         │
└─────────────────────────┘
```

The Beelinks are not rack mountable devices. But, you can use 1U cantilever shelves that mount in the rack, and then place 1 Beelink on each shelf.

## Switch

With a 3 node setup w/ Longhorn for persistent storage, Longhorn will copy data be saved over the network to nodes 2 + 3. This happens for every write operation.

- This means storage performance is limited by network speed between nodes.

If you plugged all 3 Beelinks into a Home Router, your home lab would now be competing with other:

- Phones
- Computers
- Shared bandwidth
- Higher latency
- Router CPU becomes bottleneck

A dedicated network switch is ideal for this use case to enable direct node-to-node communication and allow full bandwidth for cluster traffic.

Switches can be unmanaged or managed.

- Unmanaged is a plug and play network switch, it's dumb. You plug in power and ethernet cables and it works with no configuration, but also means you have no control or visibility.
- Managed is a network switch with a brain which is configurable via web UI, CLI, or app. You connect via web browser or SSH and can configure settings, monitor traffic, and control behavior.
  - With this, you can set up virtual LANs (VLANs) to separate devices into isolated networks on the same switch.
  - So you can prioritize the Kubernetes cluster traffic, then video streaming, then backups etc
  - And you get statistics and monitoring like bandwidth usage per port, errors, dropped packets, what devices are chatty etc.
  - Managed is recommended here.

Setup looks like:

- Plug power in Beelinks, home router, and network switch
- Plug dedicated ethernet from home router to network switch
- Plug dedicated ethernet from each beelink to network switch
- Use 2.5 GBe cables for max performance
- After initial setup, go to Home Router -> DHCP reservations and add 3 reservations for the 3 Beelinks
- Then reboot Beelinks, and they'll get assigned the IPs. These will be permanent and won't change.

Also, buy labels. These enable easy identification and ensure minimal mistakes and avoid headaches in the future

```text
[Back of rack]

 Cable 1 -> [ROUTER -> SWITCH]
 Cable 2 -> [SWITCH -> NODE1]
 Cable 3 -> [SWITCH -> NODE2]
 Cable 4 -> [SWITCH -> NODE3]
 Cable 5 -> [LAPTOP -> SWITCH]
```

## Storage

If all 3 Beelinks get 2 TB of storage attached onto the additional M.2 Slots, you should have ~8-10 TB of storage available in the cluster.

- This is fine for most workloads, but if you store security camera recordings or have media servers you might want more storage available.

This is where Network Attached Storage (NAS) comes in. This is a computer whose only job is to store files and share them over the network.

- It's a dedicated hard drive that multiple devices can access
- A personal Dropbox/Google Drive running in your house
- Can add 20+ TBs of storage

NAS typically uses RAID = Multiple drives working together

- RAID 1 (Mirror): 2 drives, same data on both
- 1 drive fails means no data loss because it's been replicated
- Usable: 50% (2x 4TB = 4TB Usable)

## Equipment

1. Beelinks
   - [Link](https://www.amazon.com/Beelink-PCle4-0-Computer-Support-Display/dp/B0DKF15XQJ?crid=1C2PAR48A38GI&dib=eyJ2IjoiMSJ9.aBD3Y_KJ-X9SmdkzpKR4ekeIZY5H58meIyxiED1IMob4fGf2wSCsDGeCS2wOGLe5Y-Oo-7220aVEiFR1T2y8qo29CEtCMbuiMs14Btqdnz9bLNjA6fZmQZFkcZtLZg2KX9qySH0h1O0tkrK9AONG30AxoPbmBkw9VxrPHEzSGVrg5FqnOhXFsp4vkGy5iLuhnIdDfmvL9kbW0HFxLgVDkkKyXBjoY1jp1dKbenchvdg.z2b-0vZKPDf0og4S1Hw2yphgDnAS1KIEHwIrnvnmgT0&dib_tag=se&keywords=beelink&qid=1761885542&sprefix=beelin%2Caps%2C174&sr=8-3)
2. Rack
   - [Link](https://www.amazon.com/RackPath-Performance-Cabinet-Network-Enclosure/dp/B0995K2KRQ?crid=2Q665EQHXJ5S3&dib=eyJ2IjoiMSJ9.IWrPGdORUJk2KSKRcT4vkVf6kLYlbVhYGqCrprOGSNwEUa76yqSYnFagfIPIFPKP5Wlh_6AEVPUAV5Tx6BJODqZDj_BkAd4asKelRS0zAy75MdHDTJSY9_cHSOvHtKASHfXXL0mvBwN-4NKChkoxCPnrm2EMjbiTKX9YhjP8IgBubJ2zyZVvcnSnB4D8XM9hF_oy4qgBOmmlE5akJmf3NGUY1Qt55_p_Sy4pykKndqg.kcQ2DPDtTBaH3lEnusUklVHflSJ3hyfAJt9xexPTFa8&dib_tag=se&keywords=12u%2Brack&qid=1761886747&sprefix=12u%2Brack%2Caps%2C168&sr=8-5&th=1)
3. Cantilever Shelves
   - [Link](https://www.amazon.com/StarTech-com-Server-Rack-Shelf-CABSHELFV1U/dp/B071KW94ZC?crid=1ELCK936SAZDD&dib=eyJ2IjoiMSJ9.hOB3UBy9rB8M93kTiRvitrv5__l5nHFXs8EZ76tMjXm9Eg10aoAdP_JUtFNse0m1pUdDvQK28bsSl7l0-LOVQUalvfRHuCoHTe3h7821YhfZ-IpLRXKIuiqeeg_k1zWIQ0HOV-Nm4PxMpL6EfICkVaLGeDRn9pL7Iduf0F22wU7iIWTjPSOWOM8Ls53XZAfdX05uD1KR6zoG5MAcU8qr2-AY7nc1AyFnSxnBQ-HghBw.i21HaGtsvG7p88qmIA-JHNKQA4uK4vx1v_npQOXNyeg&dib_tag=se&keywords=NavePoint%2B1U%2BVented%2BShelf&qid=1761886831&sprefix=navepoint%2B1u%2Bvented%2Bshelf%2B%2Caps%2C180&sr=8-6&th=1)
   - Buy x5
4. Managed Network Switch
   - [Link](https://www.amazon.com/MikroTik-CRS310-8G-2S-IN-in/dp/B0CH9NHFHS)
5. 2.5 GBe CAT cables
   - [Link](https://www.amazon.com/Cable-Matters-Snagless-Shielded-Ethernet/dp/B00HEM57ZU?crid=25QIQ2VJEBJGE&dib=eyJ2IjoiMSJ9.1wZzs3O0Ouv92PyqCpNB7e0ovkfRw7GAuojDnUKFY2vAkmk1jGFJ_gHu7hmoStxaMQk6l-0U1kTnzG4fiqweviUDG9OEJ5rsuttUt-OiQPJBKcTv2Dyq9MXAzCQom26i806Euc9cPCjraR9etSvhgUkYhH_rLz0N_S4JqB6EJQQsVXSYadCohQDKi5D_QvLzVuxOCYcyr171O_P5lpk7CXVwMj1WJ0ysv-mOUQxO3zQ.X4AbawO3aYaU7Wc8HMxBH7nahA2hluf7vtSjDc7kNj0&dib_tag=se&keywords=2.5%2Bgbe%2Bcat%2B6a%2Bcable&qid=1761888440&sprefix=2.5%2Bgbe%2Bcat%2B6a%2Bcable%2Caps%2C161&sr=8-4&th=1)
6. SSDs for extra M.2 Slots
7. Rack Equipment
   - Rack Hardware Kit for backup screws or whatever
   - Cable Ties
   - Labels
