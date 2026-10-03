
%% Simulation for pickling process
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 12 October, 2017
%%-----------------------------------------------------------------------------------------------------------

function [m_sln,C,m_surface,m_sln_remove,V] = pickling(Co,m_slno,T,V,m_surface_o,A_steel,m_steel)

masso = 0.01*m_slno*Co;
p.V = V;
p.T = T;
p.m_surface = m_surface_o;
p.A_steel = A_steel;

rho = density(T,Co(1),2);
m_sln_remove = 1e-6*m_steel*rho;

T_dipping = (10*rand()+10)*60; % [s] dipping time

if length(Co) == 3

Initial = [masso p.m_surface];
[t mass] = ode113(@rxnn,[0 T_dipping],Initial,[],p);

position = find(mass(:,4) <= p.m_surface*0.1175,1);

v1 = mass(1:position,1);
v2 = mass(1:position,2);
v3 = mass(1:position,3);
v4 = mass(1:position,4);

if length(v4) > 1

m_surface = p.m_surface*0.1175;
mHCl = interp1(v4,v1,m_surface,'linear','extrap') - 0.01*Co(1)*m_sln_remove;
mH2O = interp1(v4,v2,m_surface,'linear','extrap') - 0.01*Co(2)*m_sln_remove;
mFe = interp1(v4,v3,m_surface,'linear','extrap') - 0.01*Co(3)*m_sln_remove;

elseif length(v4) == 1

m_surface = 0;
mHCl = v1 - 0.01*Co(1)*m_sln_remove;
mH2O = v2 - 0.01*Co(2)*m_sln_remove;
mFe = v3 - 0.01*Co(3)*m_sln_remove;

else

m_surface = 0;
mHCl = 0.01*Co(1)*(m_slno - m_sln_remove);
mH2O = 0.01*Co(2)*(m_slno - m_sln_remove);
mFe = 0.01*Co(3)*(m_slno - m_sln_remove);

end

m_sln = mHCl + mH2O + mFe;
C = [mHCl mH2O mFe]*(100/m_sln);

rho = density(T,C(1),2);
V = m_sln/rho;

elseif length(Co) == 4

Initial = [masso(1) masso(3) masso(4) p.m_surface];
[t mass] = ode113(@rxna,[0 T_dipping],Initial,[],p);

mass_Znss = round(mass(:,4),1);
position = find(mass_Znss == 0,1,'first');

if length(position) == 1

m_surface = 0;
mHCl = mass(position,1) - 0.01*Co(1)*m_sln_remove;
mH2O = masso(2) - 0.01*Co(2)*m_sln_remove;
mFe = mass(position,2) - 0.01*Co(3)*m_sln_remove;
mZn = mass(position,3) - 0.01*Co(4)*m_sln_remove;
m_sln = mHCl + mH2O + mFe + mZn;
C = [mHCl mH2O mFe mZn]*(100/m_sln);

rho = density(T,C(1),2);
V = m_sln/rho;

else

m_surface = 0;
mHCl = 0.01*Co(1)*(m_slno - m_sln_remove);
mH2O = 0.01*Co(2)*(m_slno - m_sln_remove);
mFe = 0.01*Co(3)*(m_slno - m_sln_remove);
mZn = 0.01*Co(4)*(m_slno - m_sln_remove);
m_sln = mHCl + mH2O + mFe + mZn;
C = [mHCl mH2O mFe mZn]*(100/m_sln);

rho = density(T,C(1),2);
V = m_sln/rho;

end
end

return


function dmdtn = rxnn(t,Xi,p)

dmdtn = zeros(length(Xi),1);

mHCl = Xi(1);
mH2O = Xi(2);
mFe = Xi(3);
mT = sum(Xi(1:3));

% HCl concentratio [mg/L]
CHCl = mHCl*1000/p.V;

% Reaction rate [kg/(m3*s)]

k1 = 1011.2036*exp(-48846.2/(8.314*(p.T + 273.15)));
k2 = 0.2864*exp(-33057.2/(8.314*(p.T + 273.15)));

if Xi(4) <= p.m_surface*0.0001

code = 0;

else

code = 1;

end

rFeO = k1*CHCl^2*1e-3*code;
rFe = k2*CHCl^2*1e-3;

dmHCl_dt = -2*36.4609*(rFeO/71.8444 + rFe/55.8450)*p.V;
dmH2O_dt = 18.0152*rFeO*p.V/71.8444;
dmFe_dt = (rFe + 55.8450*rFeO/71.8444)*p.V;
dmFeO_dt = -rFeO*p.V;

dmdtn(1) = dmHCl_dt;
dmdtn(2) = dmH2O_dt;
dmdtn(3) = dmFe_dt;
dmdtn(4) = dmFeO_dt;

return

function dmdta = rxna(t,Xi,p)

dmdta = zeros(length(Xi),1);

mHCl = Xi(1);
mFe = Xi(2);
mZn = Xi(3);
mZns = Xi(4);

% HCl concentratio [mol/m^3]
CHCl = 1000*mHCl/(36.4609*p.V);

% Current density [A/m^2]

if mZns <= p.m_surface*0.0001

code = 0;

else

code = 1;

end

k1 = 5.9434e-009*exp(13114/(p.T + 273.15));
I = k1*CHCl*code;

% Reaction rate [kg/(m3*s)]

k2 = 0.2864*exp(-33057.2/(8.314*(p.T + 273.15)));
rFe = k2*(CHCl*36.4609)^2*1e-3;

dmHCl_dt = - 36.4609*(I*p.A_steel*t*1e-3/96485.3329 + 2*rFe*p.V/55.8450);
dmFe_dt = rFe*p.V;
dmZn_dt = 65.409*I*p.A_steel*t*1e-3/(2*96485.3329);
dmZns_dt = - dmZn_dt;

dmdta(1) = dmHCl_dt;
dmdta(2) = dmFe_dt;
dmdta(3) = dmZn_dt;
dmdta(4) = dmZns_dt;

return
