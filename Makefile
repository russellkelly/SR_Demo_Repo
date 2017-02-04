demo:	build base-container demo-container


build :
	docker build -t sr-demo .


base-container:
	#python RenderASBRConfigs.py
	docker network create --driver=bridge --subnet=192.168.1.0/24 sr-net
	docker run -d -it --network=sr-net --ip=192.168.1.2 --dns=8.8.8.8 \
	--volume `pwd`:/home/demos/sr-demo \
	-p 179:179 \
	-p 5002:5000 \
	--name srbase sr-demo
	docker exec -d srbase exabgp srdemo.conf

demo-container:
	docker run --name srdemo --rm -t --network=sr-net --ip=192.168.1.3 --dns=8.8.8.8 \
	-p 5003:5001 \
	-p 4201:4200 \
	--volume `pwd`:/home/demos/sr-demo \
        -i sr-demo bash

term:
	docker run --rm -t --network=sr-net --dns=8.8.8.8 \
	--volume `pwd`:/home/demos/sr-demo \
        -i sr-demo bash

clean:
	docker stop srbase
	docker rm srbase
	docker network rm sr-net
