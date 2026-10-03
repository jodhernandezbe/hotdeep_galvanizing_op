
%% Simulation for fluxing process
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 18 October, 2017
%%-----------------------------------------------------------------------------------------------------------

function [Q6,m_sln,C,Tsln,m_sln_remove,mHCl_added,mNH4OH_added,Vol,pH] = ...
fluxing2(m_rust,m_sln_o,Co,Tslno,m_steel,Qo,Tamb,Volo,pHo)

% Mass balance

mNH4OH_added = 0; mHCl_added = 0;

p.T = Tslno;

k1 = 4.9e-12*exp((78680.0/8.3145)*(1/298.15 - 1/(p.T + 273.15)));
k2 = 5.6e-10*exp((52140.0/8.3145)*(1/298.15 - 1/(p.T + 273.15)));
k3 = 2.1e-14*exp((92074.4/8.3145)*(1/298.15 - 1/(p.T + 273.15)));

pH = norminv(rand(),4.5,0.3);
CH = 10^(-pH);
CH_o = 10^(-pHo);

CH2O_m = 0.01*Co(5)*m_sln_o*(1/Volo);
CH2O = CH2O_m/18.0152;
molZn_o = 0.01*Co(2)*m_sln_o/65.409;
molZnOH2_o = 0.01*Co(3)*m_sln_o/99.4236;
eta1 = (k1*molZn_o*(CH2O)^2 - CH^2*molZnOH2_o)/(k1*CH2O^2 + CH^2);
molZn = molZn_o - eta1;
molZnOH2 = molZnOH2_o + eta1;

molFe_o = 0.01*Co(8)*m_sln_o/55.845 + m_rust/71.8444;
molFeOH2_o = 0.01*Co(9)*m_sln_o/89.8596;
eta3 = (k3*molFe_o*(CH2O)^2 - CH^2*molFeOH2_o)/(k3*CH2O^2 + CH^2);
molFe = molFe_o - eta3;
molFeOH2 = molFeOH2_o + eta3;

molH_rxn = m_rust*2/71.8444;

molNH4_o = 0.01*Co(4)*m_sln_o/18.0383;
molNH4OH_o = 0.01*Co(6)*m_sln_o/35.0456;

if pH <= pHo

% As CHCl - CHrxn + CH_o + 2eta1 + eta2 + 2eta3 = CH
% HCl was added to the flux bath, but NH4OH was not added to

eta2 = (k2*molNH4_o*CH2O - CH*molNH4OH_o)/(CH + k2*CH2O);

if pH > 5

A = (0.01*Co(5)*m_sln_o - (2*eta1 + eta2 + 2*eta3)*18.0152 ...
+ m_rust*18.0152/71.8444)/CH2O_m;

molHCl = (CH*A + molH_rxn - CH_o*Volo - 2*eta1 - eta2 - 2*eta3)/...
(1 - 0.63*36.4609*CH/(0.37*CH2O_m));
molNH4OH = molNH4OH_o + eta2;
molNH4 = molNH4_o - eta2;

if molHCl < 0

mHCl_added = 0; % The addition of FeO decreasing pH
molHCl = 0;
Vol = A;

else

mHCl_added = molHCl*36.4609;
Vol = A + 0.63*molHCl*36.4609/(0.37*CH2O_m);

end

else

Vol = (0.01*Co(5)*m_sln_o - (2*eta1 + eta2 + 2*eta3)*18.0152 ...
+ m_rust*18.0152/71.8444)/CH2O_m;

molNH4OH = molNH4OH_o + eta2;
molNH4 = molNH4_o - eta2;
molHCl = 0;

end

mNH4OH_added = 0;

elseif pH > pHo

% HCl was not added to the flux bath, but NH4OH was added to

if pH < 4

A = (0.01*Co(5)*m_sln_o - (2*eta1 + 2*eta3)*18.0152 ...
+ (k2*CH2O*molNH4_o/CH - molNH4OH_o)*0.7*35.0456/0.3 ...
+ m_rust*18.0152/71.8444)/CH2O_m;

eta2 = (CH*A + molH_rxn - CH_o*Volo - 2*eta1 - 2*eta3)/...
(1 + 0.7*35.0456*(k2*CH2O/CH + 1)*CH/(CH2O_m*0.3) + 18.0152*CH/CH2O_m);
molNH4 = molNH4_o - eta2;

molNH4OH = k2*molNH4*CH2O/CH;

% As molNH4OH = molNH4OH_o + molNH4OH_added + eta2

molNH4OH_added = molNH4OH - molNH4OH_o - eta2;
mNH4OH_added = molNH4OH_added*35.0456;

Vol = (0.7*molNH4OH_added*35.0456/0.3 + 0.01*Co(5)*m_sln_o - ...
(2*eta1 + eta2 + 2*eta3) + m_rust*18.0152/71.8444)/CH2O_m;

else

A = (0.01*Co(5)*m_sln_o - (2*eta1 + 2*eta3)*18.0152 ...
+ m_rust*18.0152/71.8444)/CH2O_m;

eta2 = (CH*A + molH_rxn - CH_o*Volo - 2*eta1 - 2*eta3)/...
(1 + 0.7*35.0456*(k2*CH2O/CH + 1)*CH/(CH2O_m*0.3) + 18.0152*CH/CH2O_m);
molNH4 = molNH4_o - eta2;

molNH4OH = k2*molNH4*CH2O/CH;
mNH4OH_added = 0;

Vol = (0.01*Co(5)*m_sln_o - (2*eta1 + eta2 + 2*eta3) + ...
m_rust*18.0152/71.8444)/CH2O_m;

end

molHCl = 0;
mHCl_added = 0;

end

mCl = 0.01*Co(1)*m_sln_o + molHCl*35.453;
mZn = molZn*65.409;
mZnOH2 = molZnOH2*99.4236;
mNH4 = molNH4*18.0383;
mH2O = CH2O_m*Vol;
mNH4OH = molNH4OH*35.0456;
mH = CH*1.0079*Vol;
mFe = molFe*55.845;
mFeOH2 = molFeOH2*89.8596;
m_sln = mCl + mZn + mZnOH2 + mNH4 + mH2O + mNH4OH + mH + mFe + mFeOH2;

C = [mCl mZn mZnOH2 mNH4 mH2O mNH4OH mH mFe mFeOH2]*(100/m_sln);

m_sln_remove = 1e-6*m_steel*1030;
m_sln = m_sln - m_sln_remove;

% Energy balance

lost = abs((Tslno - Tamb)/35.1);

num = (1 - 0.1*lost)*m_sln*96.232*(Tslno - 25) + 25*m_sln*96.232 + Tamb*m_steel*450 + Qo;
den = m_sln*96.232 + m_steel*450;
Tsln = num/den;

Q6 = 0.1*lost*m_sln*96.232*(Tslno - 25) + m_steel*450*(Tsln - Tamb);

return
